import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.email or self.username


class OTPVerification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_valid(self):
        return timezone.now() <= self.expires_at and self.verified_at is None

    @classmethod
    def generate_for_user(cls, user):
        code = str(random.randint(100000, 999999))
        otp = cls.objects.create(user=user, code=code, expires_at=timezone.now() + timedelta(minutes=5))
        return otp

    def __str__(self):
        return f'{self.user.email} - {self.code}'
