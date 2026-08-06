from django.core.management.base import BaseCommand
from reports.models import CrimeType


class Command(BaseCommand):
    help = 'Seed default crime types'

    def handle(self, *args, **options):
        crime_types = [
            'Armed Robbery',
            'Theft',
            'Domestic Violence',
            'Burglary',
            'Cybercrime',
            'Murder',
            'Kidnapping',
            'Drug Offense',
            'Sexual Assault',
            'Assault',
            'Traffic Incident',
            'Terrorism',
            'Fraud',
            'Missing Person',
            'Vandalism',
            'Fire Incident',
            'Public Disturbance',
            'Other',
        ]
        for name in crime_types:
            CrimeType.objects.get_or_create(name=name, defaults={'slug': name.lower().replace(' ', '-')})
        self.stdout.write(self.style.SUCCESS('Crime types seeded successfully.'))