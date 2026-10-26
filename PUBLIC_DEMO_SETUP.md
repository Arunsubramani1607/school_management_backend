# Public demo environment setup

Use the current application as a demo environment only. Do not put real school
data in it or use the institution super-admin account as the public demo login.
If you later launch a production school service, create a separate backend,
database, and frontend project for it.

## Render services

1. Create a Render PostgreSQL database in the same region as the demo backend.
2. Set `DATABASE_URL` on the backend to that database's **internal** connection
   URL. The backend uses PostgreSQL when `DATABASE_URL` is set and SQLite for
   local development otherwise.
3. Attach a persistent disk to the backend with mount path `/var/data`. This
   stores uploaded media and the private JSON recovery backup.
4. Set the backend Start Command to `/app/docker-entrypoint.sh` if a custom
   Start Command is configured in Render.
5. Set the following backend environment variables:

```text
DEBUG=false
SECRET_KEY=<a new random secret, at least 50 characters>
ALLOWED_HOSTS=school-management-backend-gsza.onrender.com
CORS_ALLOWED_ORIGINS=https://school-management-frontend-woad.vercel.app
CSRF_TRUSTED_ORIGINS=https://school-management-frontend-woad.vercel.app
APP_DATA_DIR=/var/data
JSON_DATABASE_BACKUP=/var/data/school_data_backup.json
JSON_DATABASE_BACKUP_INTERVAL=300
DEMO_MODE=true
BOOTSTRAP_SUPER_ADMIN_EMAIL=<private institution admin email>
BOOTSTRAP_SUPER_ADMIN_PASSWORD=<private password, at least 12 characters>
DEMO_ADMIN_EMAIL=demo.admin@demo.example.test
DEMO_ADMIN_PASSWORD=DemoOnly2026!
RAZORPAY_ENABLED=false
RAZORPAY_TEST_MODE=true
WHATSAPP_ALERTS_ENABLED=false
```

The current Vercel frontend already calls this backend URL. If the backend URL
changes later, update `NEXT_PUBLIC_API_URL` and the CORS/CSRF origins above.
Set these Vercel environment variables for the public demo build:

```text
NEXT_PUBLIC_API_URL=https://school-management-backend-gsza.onrender.com/api
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_DEMO_ADMIN_EMAIL=demo.admin@demo.example.test
NEXT_PUBLIC_DEMO_ADMIN_PASSWORD=DemoOnly2026!
```

The login page will display and fill the shared demo credentials when these
variables are enabled. They are public by design; never put the super-admin
password in a `NEXT_PUBLIC_` variable.

## Demo data and accounts

At startup, the service migrates the database, restores a JSON fixture if the
application database is empty, bootstraps the private super-admin only if one
does not exist, and seeds synthetic demo records when `DEMO_MODE=true`. The
seed contains Demo School, academic year 2026–2027, 12 classes, 24 sections,
24 teachers, 48 students, 8 staff, subjects, and five weekdays of student,
teacher, and staff attendance. The school/admin registration endpoints require
an authenticated super-admin; public super-admin registration is removed.

The demo admin password is intentionally public and can be shared with testers.
Keep the super-admin password private. Demo teacher,
student, and staff profiles use synthetic contact details and passwords based
on their synthetic contact numbers.

For a disposable shared demo, add a Render Cron Job that runs
`python manage.py reset_demo_school` once each night. Give that cron service
the demo backend's `DATABASE_URL`, `DEMO_MODE=true`, `DEMO_ADMIN_EMAIL`,
`DEMO_ADMIN_PASSWORD`, `BOOTSTRAP_SUPER_ADMIN_EMAIL`, and
`BOOTSTRAP_SUPER_ADMIN_PASSWORD` environment variables. The command refuses to
run unless demo mode is enabled and flushes the entire database, so use it only
for the dedicated demo database.

## Backups and secrets

The database is backed up to a private JSON fixture every five minutes. The
backup is excluded from Git and the Docker build context. It contains personal
demo records and password hashes, so do not publish it or commit it. Render's
PostgreSQL backups are the recovery option for the database; the JSON fixture
is an additional recovery copy for restoring an empty application database.

Payment integrations are disabled by default. The old Razorpay values were
present in source defaults; rotate any keys that were real, and add only new
test credentials through Render environment variables if the demo needs
payment screens.

The earlier live demo rows are no longer present, so they cannot be recovered
from the old SQLite database. This seed command recreates the synthetic demo
dataset on the new demo service.
