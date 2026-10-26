import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create the first super-admin from private environment variables.'

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.getenv('BOOTSTRAP_SUPER_ADMIN_EMAIL', '').strip().lower()
        password = os.getenv('BOOTSTRAP_SUPER_ADMIN_PASSWORD', '')
        name = os.getenv('BOOTSTRAP_SUPER_ADMIN_NAME', 'Institution Admin').strip()

        existing = User.objects.filter(user_type='super_admin').order_by('id').first()
        if existing:
            existing_email = (existing.email or existing.username).lower()
            if email and password and existing_email == email:
                if len(password) < 12:
                    raise CommandError('BOOTSTRAP_SUPER_ADMIN_PASSWORD must be at least 12 characters.')
                if not existing.check_password(password):
                    existing.set_password(password)
                    existing.save(update_fields=['password'])
                    self.stdout.write('Updated the configured super-admin password.')
                else:
                    self.stdout.write('Configured super-admin already exists; bootstrap skipped.')
                return
            self.stdout.write('A super-admin already exists; bootstrap skipped.')
            return

        if not email or not password:
            self.stdout.write('Super-admin bootstrap skipped; private email/password variables are unset.')
            return
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise CommandError('The bootstrap email already belongs to another account.')
        if len(password) < 12:
            raise CommandError('BOOTSTRAP_SUPER_ADMIN_PASSWORD must be at least 12 characters.')

        User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
            user_type='super_admin',
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Created the initial super-admin account {email}.'))
