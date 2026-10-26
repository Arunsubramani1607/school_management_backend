import json
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connections, transaction


class Command(BaseCommand):
    help = 'Write a private JSON fixture backup of the application database.'

    def handle(self, *args, **options):
        target = Path(settings.JSON_DATABASE_BACKUP)
        target.parent.mkdir(parents=True, exist_ok=True)
        connection = connections['default']
        connection.ensure_connection()

        fd, temp_name = tempfile.mkstemp(
            prefix=f'.{target.name}.',
            suffix='.tmp',
            dir=str(target.parent),
        )
        os.close(fd)
        temp_path = Path(temp_name)

        try:
            with temp_path.open('w', encoding='utf-8') as output:
                with transaction.atomic():
                    call_command(
                        'dumpdata',
                        use_natural_foreign_keys=True,
                        use_natural_primary_keys=True,
                        exclude=[
                            'contenttypes',
                            'auth.permission',
                            'sessions.session',
                            'authtoken.token',
                            'accounts.passwordresetotp',
                        ],
                        stdout=output,
                        verbosity=0,
                    )
                output.flush()
                os.fsync(output.fileno())

            # Validate the generated fixture before replacing the previous backup.
            with temp_path.open('r', encoding='utf-8') as fixture:
                json.load(fixture)
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass
            os.replace(temp_path, target)
        finally:
            if temp_path.exists():
                temp_path.unlink()

        self.stdout.write(self.style.SUCCESS(f'JSON database backup saved to {target}'))
