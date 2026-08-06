# from django.db import transaction
# from django.utils import timezone

# from .models import Notification, Report, ReportTimeline
# from .utils import generate_tracking_code
# from dashboard.models import SystemLog


# class ReportService:
#     @staticmethod
#     def build_tracking_code():
#         return generate_tracking_code()

#     @classmethod
#     @transaction.atomic
#     def create_report(cls, data, requester=None):
#         anonymous = data.get('anonymous', False)
#         reporter = requester if requester and requester.is_authenticated and not anonymous else None

#         report = Report.objects.create(
#             crime_type=data['crime_type'],
#             description=data['description'],
#             incident_datetime=data.get('incident_datetime', timezone.now()),
#             address=data['address'],
#             latitude=data['latitude'],
#             longitude=data['longitude'],
#             anonymous=anonymous,
#             reporter=reporter,
#             status=Report.STATUS_PENDING,
#             priority=data.get('priority', Report.PRIORITY_MEDIUM),
#         )
#         report.tracking_code = cls.build_tracking_code()
#         report.save(update_fields=['tracking_code'])

#         cls.create_timeline(
#             report, note='Report submitted.', updated_by=requester)
#         cls.create_notification(report, 'submitted', requester)
#         return report

#     @staticmethod
#     def create_timeline(report, status=None, note='', updated_by=None):
#         status = status or report.status
#         return ReportTimeline.objects.create(report=report, status=status, note=note, updated_by=updated_by)

#     @staticmethod
#     def create_notification(report, action, user=None):
#         if action == 'submitted':
#             title = 'Report Submitted'
#             message = f'Your report {report.tracking_code} has been received and is pending review.'
#         elif action == 'verified':
#             title = 'Report Verified'
#             message = f'Your report {report.tracking_code} has been verified.'
#         elif action == 'rejected':
#             title = 'Report Rejected'
#             message = f'Your report {report.tracking_code} was rejected.'
#         elif action == 'resolved':
#             title = 'Report Resolved'
#             message = f'Your report {report.tracking_code} has been resolved.'
#         else:
#             return None

#         if report.reporter_id:
#             return Notification.objects.create(user=report.reporter, title=title, message=message)
#         if user and getattr(user, 'is_authenticated', False):
#             return Notification.objects.create(user=user, title=title, message=message)
#         return None

#     @classmethod
#     @transaction.atomic
#     def update_status(cls, report, status, updated_by=None, note=''):
#         old_status = report.status
#         report.status = status
#         report.save(update_fields=['status', 'updated_at'])
#         cls.create_timeline(
#             report, status=status, note=note or f'Status changed from {old_status} to {status}.', updated_by=updated_by)
#         SystemLog.objects.create(
#             admin=updated_by if updated_by and updated_by.is_authenticated else None,
#             action=f'{updated_by.email if updated_by else "System"} changed report {report.tracking_code} from {old_status} to {status}',
#             target_report_id=report.id,
#         )

#         if status == Report.STATUS_VERIFIED:
#             cls.create_notification(report, 'verified', updated_by)
#         elif status == Report.STATUS_REJECTED:
#             cls.create_notification(report, 'rejected', updated_by)
#         elif status == Report.STATUS_RESOLVED:
#             cls.create_notification(report, 'resolved', updated_by)
#         return report


from django.db import transaction
from django.utils import timezone

from .models import CrimeType, Notification, Report, ReportTimeline
from .utils import generate_tracking_code
from .ai_client import classify_report, sync_report_to_ai, classify_audio
from dashboard.models import SystemLog

SEVERITY_TO_PRIORITY = {
    'Critical': Report.PRIORITY_CRITICAL,
    'High': Report.PRIORITY_HIGH,
    'Medium': Report.PRIORITY_MEDIUM,
    'Low': Report.PRIORITY_LOW,
}


class ReportService:
    @staticmethod
    def build_tracking_code():
        return generate_tracking_code()

    @classmethod
    @transaction.atomic
    def create_report(cls, data, requester=None):
        anonymous = data.get('anonymous', False)
        reporter = requester if requester and requester.is_authenticated and not anonymous else None

        ai_result = classify_report(data['description'])

        crime_type = data.get('crime_type')
        priority = data.get('priority', Report.PRIORITY_MEDIUM)

        if ai_result:
            if not crime_type and ai_result.get('crime_type'):
                ai_type_name = ai_result['crime_type']
                if ai_type_name == 'Unknown':
                    ai_type_name = 'Other'
                crime_type = CrimeType.objects.filter(
                    name=ai_type_name, is_active=True).first()

            if ai_result.get('severity'):
                priority = SEVERITY_TO_PRIORITY.get(
                    ai_result['severity'], priority)

        if not crime_type:
            crime_type = CrimeType.objects.filter(
                name='Other', is_active=True).first()

        report = Report.objects.create(
            crime_type=crime_type,
            description=data['description'],
            incident_datetime=data.get('incident_datetime', timezone.now()),
            address=data['address'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            anonymous=anonymous,
            reporter=reporter,
            status=Report.STATUS_PENDING,
            priority=priority,
        )
        report.tracking_code = cls.build_tracking_code()
        report.save(update_fields=['tracking_code'])

        cls.create_timeline(
            report, note='Report submitted.', updated_by=requester)
        cls.create_notification(report, 'submitted', requester)

        sync_result = sync_report_to_ai(
            report.description, report.latitude, report.longitude, report.address)

        if sync_result:
            report.recommended_dispatch_unit = sync_result.get(
                'recommended_dispatch_unit', '')
            report.detected_language = sync_result.get('detected_language', '')
            report.translated_description = sync_result.get(
                'translated_report', '')
            report.ai_verification_confidence = sync_result.get(
                'verification_confidence')
            report.state = sync_result.get('state', '')
            report.save(update_fields=[
                'recommended_dispatch_unit', 'detected_language',
                'translated_description', 'ai_verification_confidence', 'state',
            ])

        return report

    @staticmethod
    def create_timeline(report, status=None, note='', updated_by=None):
        status = status or report.status
        return ReportTimeline.objects.create(report=report, status=status, note=note, updated_by=updated_by)

    @staticmethod
    def create_notification(report, action, user=None):
        if action == 'submitted':
            title = 'Report Submitted'
            message = f'Your report {report.tracking_code} has been received and is pending review.'
        elif action == 'verified':
            title = 'Report Verified'
            message = f'Your report {report.tracking_code} has been verified.'
        elif action == 'rejected':
            title = 'Report Rejected'
            message = f'Your report {report.tracking_code} was rejected.'
        elif action == 'resolved':
            title = 'Report Resolved'
            message = f'Your report {report.tracking_code} has been resolved.'
        else:
            return None

        if report.reporter_id:
            return Notification.objects.create(user=report.reporter, title=title, message=message)
        if user and getattr(user, 'is_authenticated', False):
            return Notification.objects.create(user=user, title=title, message=message)
        return None

    @classmethod
    @transaction.atomic
    def update_status(cls, report, status, updated_by=None, note=''):
        old_status = report.status
        report.status = status
        report.save(update_fields=['status', 'updated_at'])
        cls.create_timeline(
            report, status=status, note=note or f'Status changed from {old_status} to {status}.', updated_by=updated_by)
        SystemLog.objects.create(
            admin=updated_by if updated_by and updated_by.is_authenticated else None,
            action=f'{updated_by.email if updated_by else "System"} changed report {report.tracking_code} from {old_status} to {status}',
            target_report_id=report.id,
        )

        if status == Report.STATUS_VERIFIED:
            cls.create_notification(report, 'verified', updated_by)
        elif status == Report.STATUS_REJECTED:
            cls.create_notification(report, 'rejected', updated_by)
        elif status == Report.STATUS_RESOLVED:
            cls.create_notification(report, 'resolved', updated_by)
        return report


    @classmethod
    @transaction.atomic
    def create_report_from_audio(cls, audio_file, address, latitude, longitude, requester=None, anonymous=False):
        audio_result, error_message = classify_audio(audio_file)
        print("Audio result:", audio_result)
        print("Error:", error_message)

        if not audio_result:
            raise ValueError(error_message or "Could not process the audio. Please try again.")

        description = audio_result.get('transcribed_text', '')
        print("Description:", repr(description))
        ai_type_name = audio_result.get('crime_type', 'Unknown')
        if ai_type_name == 'Unknown':
            ai_type_name = 'Other'
        crime_type = CrimeType.objects.filter(
            name=ai_type_name, is_active=True).first()
        if not crime_type:
            crime_type = CrimeType.objects.filter(
                name='Other', is_active=True).first()

        priority = SEVERITY_TO_PRIORITY.get(
            audio_result.get('severity'), Report.PRIORITY_MEDIUM)
        reporter = requester if requester and requester.is_authenticated and not anonymous else None

        report = Report.objects.create(
            crime_type=crime_type,
            description=description,
            incident_datetime=timezone.now(),
            address=address,
            latitude=latitude,
            longitude=longitude,
            anonymous=anonymous,
            reporter=reporter,
            status=Report.STATUS_PENDING,
            priority=priority,
            recommended_dispatch_unit=audio_result.get(
                'recommended_dispatch_unit', ''),
            detected_language=audio_result.get('detected_language', ''),
            translated_description=audio_result.get('translated_report', ''),
        )
        report.tracking_code = cls.build_tracking_code()
        report.save(update_fields=['tracking_code'])

        cls.create_timeline(
            report, note='Report submitted via voice.', updated_by=requester)
        cls.create_notification(report, 'submitted', requester)

        sync_result = sync_report_to_ai(
            report.description, report.latitude, report.longitude, report.address)
        if sync_result:
            report.ai_verification_confidence = sync_result.get(
                'verification_confidence')
            report.state = sync_result.get('state', '')
            report.save(update_fields=['ai_verification_confidence', 'state'])

        return report
