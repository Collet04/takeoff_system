# TakeOFF Driver Onboarding Assessment

This project is a small Django-based driver onboarding MVP for the TakeOFF assessment. It includes registration, OTP verification, onboarding steps, document upload, review, application status, and admin review flow.

## Features
- User registration with email + password
- Functional OTP verification with 5-minute expiry
- Login/logout using Django auth
- Driver personal details capture
- Identity verification with file upload
- Vehicle details collection
- Driver and vehicle document upload
- Review and submission workflow
- Dashboard and application status view
- Seeded fictional test driver profiles
- Django admin integration

## Architecture
- `auth_app`: authentication, OTP, registration, login
- `driver_app`: driver profile, application lifecycle, vehicle, document storage, review logic

## Running locally
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_test_data
python manage.py runserver
```

## Admin
Visit `/admin/` and sign in with the superuser account.

## Test credentials
The seeded accounts are fictional:
- tawanda.demo@example.com / demo12345
- rudo.demo@example.com / demo12345
- brian.demo@example.com / demo12345

## OTP behavior
OTP codes are generated at signup and shown in the Django console output during development. They expire after 5 minutes. This is configured via `EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`.

## Deployment note
This project is configured for local SQLite development and is structured to move to PostgreSQL in production by updating the database settings.

## Known limitations
- Documents are stored locally in `MEDIA_ROOT` for development.
- The current implementation keeps the assessment focused on a functional onboarding MVP rather than a full production-grade logistics system.
