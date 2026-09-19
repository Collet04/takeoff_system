from django.core.management.base import BaseCommand
from django.utils import timezone

from auth_app.models import User
from driver_app.models import DriverApplication, DriverDocument, DriverProfile, Vehicle, VehicleDocument


class Command(BaseCommand):
    help = 'Seed fictional TakeOFF driver profiles for assessment demos.'

    def handle(self, *args, **options):
        profiles = [
            {
                'first_name': 'Tawanda',
                'last_name': 'Moyo',
                'email': 'tawanda.demo@example.com',
                'phone': '+263770000001',
                'identity': 'TEST-ZW-ID-001',
                'vehicle_make': 'Toyota',
                'vehicle_model': 'Hilux',
                'registration': 'TEST-1234',
                'application_reference': 'TKO-2026-00001',
                'status': 'UNDER_REVIEW',
            },
            {
                'first_name': 'Rudo',
                'last_name': 'Ncube',
                'email': 'rudo.demo@example.com',
                'phone': '+263770000002',
                'identity': 'TEST-ZW-ID-002',
                'vehicle_make': 'Honda',
                'vehicle_model': 'Fit',
                'registration': 'TEST-1235',
                'application_reference': 'TKO-2026-00002',
                'status': 'APPROVED',
            },
            {
                'first_name': 'Brian',
                'last_name': 'Dube',
                'email': 'brian.demo@example.com',
                'phone': '+263770000003',
                'identity': 'TEST-ZW-ID-003',
                'vehicle_make': 'Toyota',
                'vehicle_model': 'Hiace',
                'registration': 'TEST-1236',
                'application_reference': 'TKO-2026-00003',
                'status': 'SUBMITTED',
            },
        ]

        for profile_data in profiles:
            user, created = User.objects.get_or_create(
                email=profile_data['email'],
                defaults={
                    'username': profile_data['email'],
                    'first_name': profile_data['first_name'],
                    'last_name': profile_data['last_name'],
                    'password': 'demo12345',
                    'phone_number': profile_data['phone'],
                    'is_active': True,
                },
            )
            if created:
                user.set_password('demo12345')
                user.save()

            DriverProfile.objects.update_or_create(
                user=user,
                defaults={
                    'first_name': profile_data['first_name'],
                    'last_name': profile_data['last_name'],
                    'phone_number': profile_data['phone'],
                    'email': profile_data['email'],
                    'residential_address': '123 Fictional Road',
                    'city': 'Harare',
                    'province': 'Harare',
                    'nationality': 'Zimbabwean',
                    'gender': 'male',
                },
            )

            app, _ = DriverApplication.objects.update_or_create(
                driver=user,
                defaults={
                    'application_reference': profile_data['application_reference'],
                    'status': profile_data['status'],
                    'identity_document_type': 'National ID',
                    'identity_document_number': profile_data['identity'],
                    'submitted_at': timezone.now(),
                },
            )

            vehicle, _ = Vehicle.objects.update_or_create(
                application=app,
                defaults={
                    'vehicle_type': 'Pickup',
                    'make': profile_data['vehicle_make'],
                    'model': profile_data['vehicle_model'],
                    'year': 2020,
                    'colour': 'White',
                    'registration_number': profile_data['registration'],
                    'vin_chassis_number': 'TEST-VIN-001',
                    'max_cargo_capacity': '500kg',
                },
            )

            for doc_type in [
                "Driver's Licence",
                'Proof of Address',
                'Driver Clearance',
            ]:
                DriverDocument.objects.get_or_create(
                    application=app,
                    document_type=doc_type,
                    defaults={'file': 'test_driver_license.pdf'},
                )

            for doc_type in [
                'Vehicle Registration',
                'Vehicle Insurance',
                'Vehicle Inspection',
            ]:
                VehicleDocument.objects.get_or_create(
                    vehicle=vehicle,
                    document_type=doc_type,
                    defaults={'file': 'test_vehicle_registration.pdf'},
                )

        self.stdout.write(self.style.SUCCESS('Seed data created successfully.'))
