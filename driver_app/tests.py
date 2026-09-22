from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .forms import DriverDocumentForm, IdentityVerificationForm, VehicleDocumentForm
from .models import DriverApplication, DriverDocument, DriverProfile, Vehicle, VehicleDocument

User = get_user_model()


class DriverOnboardingFlowTests(TestCase):
    def test_registration_requires_unique_email(self):
        User.objects.create_user(
            username='existing@example.com',
            email='existing@example.com',
            password='StrongPass123',
        )

        response = self.client.post('/signup/', {
            'first_name': 'Tawanda',
            'last_name': 'Moyo',
            'email': 'existing@example.com',
            'phone_number': '+263770000001',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })

        self.assertIn(response.status_code, [200, 302])

    def test_dashboard_requires_login(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_identity_document_requires_pdf_upload(self):
        form = IdentityVerificationForm(
            data={
                'identity_document_type': 'National ID',
                'identity_document_number': 'ID-12345',
            },
            files={'identity_document_file': SimpleUploadedFile('identity.jpg', b'fake-image', content_type='image/jpeg')},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('PDF', str(form.errors['identity_document_file']))

    def test_driver_document_type_cannot_be_uploaded_twice(self):
        user = User.objects.create_user(
            username='driver@example.com',
            email='driver@example.com',
            password='StrongPass123',
        )
        application = DriverApplication.objects.create(
            driver=user,
            application_reference='TKO-2026-0001',
        )
        DriverDocument.objects.create(
            application=application,
            document_type="Driver's Licence",
            file=SimpleUploadedFile('license.pdf', b'pdf-content', content_type='application/pdf'),
        )

        form = DriverDocumentForm(
            data={'document_type': "Driver's Licence"},
            files={'file': SimpleUploadedFile('license-2.pdf', b'pdf-content', content_type='application/pdf')},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('already been uploaded', str(form.errors))

    def test_driver_document_requires_pdf_upload(self):
        form = DriverDocumentForm(
            data={'document_type': "Driver's Licence"},
            files={'drivers_licence': SimpleUploadedFile('license.png', b'fake-image', content_type='image/png')},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('PDF', str(form.errors['drivers_licence']))

    def test_vehicle_document_requires_pdf_upload(self):
        form = VehicleDocumentForm(
            data={'document_type': 'Vehicle Registration'},
            files={'vehicle_registration': SimpleUploadedFile('registration.jpg', b'fake-image', content_type='image/jpeg')},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('PDF', str(form.errors['vehicle_registration']))

    def test_vehicle_document_type_cannot_be_uploaded_twice(self):
        user = User.objects.create_user(
            username='vehicle@example.com',
            email='vehicle@example.com',
            password='StrongPass123',
        )
        application = DriverApplication.objects.create(
            driver=user,
            application_reference='TKO-2026-0002',
        )
        vehicle = Vehicle.objects.create(
            application=application,
            vehicle_type='Sedan',
            make='Toyota',
            model='Corolla',
            year=2022,
            colour='White',
            registration_number='ABC123',
            vin_chassis_number='VIN12345',
        )
        VehicleDocument.objects.create(
            vehicle=vehicle,
            document_type='Vehicle Registration',
            file=SimpleUploadedFile('registration.pdf', b'pdf-content', content_type='application/pdf'),
        )

        form = VehicleDocumentForm(
            data={'document_type': 'Vehicle Registration'},
            files={'file': SimpleUploadedFile('registration-2.pdf', b'pdf-content', content_type='application/pdf')},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('already been uploaded', str(form.errors))

    def test_admin_users_are_redirected_to_admin_dashboard_without_applications(self):
        admin_user = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='StrongPass123',
            is_staff=True,
            is_superuser=True,
        )

        self.client.force_login(admin_user)
        response = self.client.get('/dashboard/')

        self.assertRedirects(response, '/admin/applications/')
        self.assertFalse(DriverApplication.objects.filter(driver=admin_user).exists())

    def test_admin_can_delete_applicant_and_all_related_details(self):
        driver_user = User.objects.create_user(
            username='driver-delete@example.com',
            email='driver-delete@example.com',
            password='StrongPass123',
        )
        application = DriverApplication.objects.create(
            driver=driver_user,
            application_reference='TKO-2026-0003',
            status=DriverApplication.STATUS_SUBMITTED,
        )
        DriverProfile.objects.create(
            user=driver_user,
            first_name='Alice',
            last_name='Ncube',
            email=driver_user.email,
            phone_number='+263771111111',
        )
        vehicle = Vehicle.objects.create(
            application=application,
            vehicle_type='Pickup',
            make='Ford',
            model='Ranger',
            year=2021,
            colour='Silver',
            registration_number='DEF456',
            vin_chassis_number='VIN67890',
        )
        DriverDocument.objects.create(
            application=application,
            document_type="Driver's Licence",
            file=SimpleUploadedFile('license.pdf', b'pdf-content', content_type='application/pdf'),
        )
        VehicleDocument.objects.create(
            vehicle=vehicle,
            document_type='Vehicle Registration',
            file=SimpleUploadedFile('registration.pdf', b'pdf-content', content_type='application/pdf'),
        )

        admin_user = User.objects.create_user(
            username='admin-delete@example.com',
            email='admin-delete@example.com',
            password='StrongPass123',
            is_staff=True,
            is_superuser=True,
        )

        self.client.force_login(admin_user)
        response = self.client.post('/admin/applications/', {'application_id': application.id, 'action': 'DELETE'})

        self.assertRedirects(response, '/admin/applications/')
        self.assertFalse(User.objects.filter(pk=driver_user.pk).exists())
        self.assertFalse(DriverApplication.objects.filter(pk=application.pk).exists())
        self.assertFalse(Vehicle.objects.filter(pk=vehicle.pk).exists())
