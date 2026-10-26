import os

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

class Command(BaseCommand):
    help = 'Reset the isolated demo database and repopulate its synthetic sample data.'

    @transaction.atomic
    def handle(self, *args, **options):
        if os.getenv('DEMO_MODE', '').strip().lower() not in {'1', 'true', 'yes', 'on'}:
            raise CommandError('Refusing to reset data unless DEMO_MODE=true.')

        # This command is only for the dedicated DEMO_MODE database. Flush all
        # test activity so that the shared public demo returns to a known state.
        call_command('flush', interactive=False, verbosity=0)
        call_command('bootstrap_super_admin')
        call_command('seed_demo_school')
        self.stdout.write(self.style.SUCCESS('Demo database has been reset and reseeded.'))
