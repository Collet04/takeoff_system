from django.contrib import admin

from .models import OTPVerification


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'expires_at', 'verified_at')
    search_fields = ('user__email', 'code')
    list_filter = ('verified_at', 'created_at')
    readonly_fields = ('created_at', 'expires_at', 'verified_at')
