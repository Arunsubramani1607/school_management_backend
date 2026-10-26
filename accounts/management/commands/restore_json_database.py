import json
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction


INFRASTRUCTURE_APPS = {
    'admin',
    'auth',
    'contenttypes',
    'sessions',
    'authtoken',
}


def has_application_data():
    for model in apps.get_models():
        if model._meta.proxy or model._meta.app_label in INFRASTRUCTURE_APPS:
            continue
        if model.objects.exists():
            return True
    return False


class Command(BaseCommand):
    help = 'Restore the JSON database backup only when the application database is empty.'

    def handle(self, *args, **options):
        backup = Path(settings.JSON_DATABASE_BACKUP)
        if not backup.is_file():
            self.stdout.write('No JSON database backup found; starting with the current database.')
            return

        if has_application_data():
            self.stdout.write('Application data already exists; JSON restore skipped.')
            return

        try:
            with backup.open('r', encoding='utf-8') as fixture:
                rows = json.load(fixture)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f'Cannot read JSON database backup at {backup}: {exc}') from exc

        if not isinstance(rows, list) or not rows:
            self.stdout.write('JSON database backup is empty; no restore performed.')
            return

        with transaction.atomic():
            call_command('loaddata', str(backup), verbosity=1)

        self.stdout.write(self.style.SUCCESS(f'Restored application data from {backup}'))
