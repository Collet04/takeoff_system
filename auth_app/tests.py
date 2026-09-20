from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

User = get_user_model()


class AuthFlowTests(TestCase):
    def test_register_user(self):
        response = self.client.post('/signup/', {
            'first_name': 'Tawanda',
            'last_name': 'Moyo',
            'email': 'tawanda.demo@example.com',
            'phone_number': '+263770000001',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(User.objects.filter(email='tawanda.demo@example.com').exists())

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username='existing@example.com', email='existing@example.com', password='StrongPass123')
        response = self.client.post('/signup/', {
            'first_name': 'Rudo',
            'last_name': 'Ncube',
            'email': 'existing@example.com',
            'phone_number': '+263770000002',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })
        self.assertIn(response.status_code, [200])

    def test_duplicate_email_case_insensitive_rejected(self):
        User.objects.create_user(username='caseuser@example.com', email='CaseUser@Example.com', password='StrongPass123')
        response = self.client.post('/signup/', {
            'first_name': 'Case',
            'last_name': 'User',
            'email': 'caseuser@example.com',
            'phone_number': '+263770000004',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')

    def test_signup_sends_otp_email(self):
        response = self.client.post('/signup/', {
            'first_name': 'Email',
            'last_name': 'Driver',
            'email': 'email.driver@example.com',
            'phone_number': '+263770000005',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['email.driver@example.com'])
        self.assertIn('verification code', mail.outbox[0].body)

        code = mail.outbox[0].body.split('verification code is ')[1].split('.')[0]
        verify_response = self.client.post('/verify-otp/', {'otp_code': code})
        self.assertRedirects(verify_response, '/dashboard/')
        self.assertTrue(User.objects.get(email='email.driver@example.com').is_active)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_unverified_login_redirects_to_otp(self):
        user = User.objects.create_user(
            username='pending@example.com',
            email='pending@example.com',
            password='StrongPass123',
            is_active=False,
        )
        response = self.client.post('/login/', {
            'username': 'pending@example.com',
            'password': 'StrongPass123',
        })
        self.assertRedirects(response, '/verify-otp/')
        self.assertTrue(self.client.session.get('pending_user_id'))
        self.assertEqual(len(mail.outbox), 1)

    @patch('auth_app.views.send_mail', side_effect=Exception('SMTP failed'))
    def test_signup_does_not_crash_when_email_send_fails(self, mock_send_mail):
        response = self.client.post('/signup/', {
            'first_name': 'NoMail',
            'last_name': 'User',
            'email': 'nomail.user@example.com',
            'phone_number': '+263770000006',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='nomail.user@example.com').exists())
        mock_send_mail.assert_called_once()
