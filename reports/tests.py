from django.core.exceptions import ValidationError
from django.test import TestCase

from reports.models import CrimeType, Report


class ReportCreationTests(TestCase):
    def setUp(self):
        self.crime_type = CrimeType.objects.create(name='Robbery', slug='robbery')

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
