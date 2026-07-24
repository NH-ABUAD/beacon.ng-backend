from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from reports.models import CrimeType, Report
from reports.services import ReportService


class ReportCreationTests(TestCase):
    def setUp(self):
        self.crime_type = CrimeType.objects.create(name='Robbery', slug='robbery')
        self.user = get_user_model().objects.create_user(email='reporter@example.com', password='testpass123')

    def test_anonymous_report_is_created_with_tracking_code(self):
        report = Report.objects.create(
            crime_type=self.crime_type,
            description='A detailed incident description that meets the minimum length requirement.',
            incident_datetime='2026-07-09T12:00:00Z',
            address='Lagos Island',
            latitude='6.5244',
            longitude='3.3792',
            anonymous=True,
        )

        self.assertTrue(report.tracking_code.startswith('BCR-'))
        self.assertEqual(report.status, Report.STATUS_PENDING)
        self.assertIsNone(report.reporter)

    def test_anonymous_reports_created_via_service_do_not_attach_reporter(self):
        report = ReportService.create_report(
            {
                'crime_type': self.crime_type,
                'description': 'A detailed incident description that meets the minimum length requirement.',
                'incident_datetime': '2026-07-09T12:00:00Z',
                'address': 'Lagos Island',
                'latitude': '6.5244',
                'longitude': '3.3792',
                'anonymous': True,
            },
            requester=self.user,
        )

        self.assertTrue(report.anonymous)
        self.assertIsNone(report.reporter)

    def test_invalid_coordinates_are_rejected(self):
        report = Report(
            crime_type=self.crime_type,
            description='A detailed incident description that meets the minimum length requirement.',
            incident_datetime='2026-07-09T12:00:00Z',
            address='Lagos Island',
            latitude='91.0',
            longitude='3.3792',
        )

        with self.assertRaises(ValidationError):
            report.full_clean()
