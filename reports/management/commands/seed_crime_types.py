from django.core.management.base import BaseCommand

from reports.models import CrimeType


class Command(BaseCommand):
    help = 'Seed default crime types'

    def handle(self, *args, **options):
        crime_types = [
            'Robbery',
            'Theft',
            'Kidnapping',
            'Armed Robbery',
            'Other',
        ]
        for name in crime_types:
            CrimeType.objects.get_or_create(name=name, defaults={'slug': name.lower().replace(' ', '-')})
        self.stdout.write(self.style.SUCCESS('Crime types seeded successfully.'))
