from django.contrib import admin

from .models import DriverApplication, DriverDocument, DriverProfile, Vehicle, VehicleDocument


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone_number', 'email', 'city', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    list_filter = ('city', 'province')


@admin.register(DriverApplication)
class DriverApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_reference', 'driver', 'status', 'created_at', 'submitted_at', 'reviewed_at')
    list_filter = ('status', 'created_at', 'submitted_at')
    search_fields = ('application_reference', 'driver__email', 'driver__username')
    readonly_fields = ('application_reference', 'created_at', 'updated_at', 'submitted_at', 'reviewed_at')

    actions = ['mark_under_review', 'approve_application', 'reject_application']

    def mark_under_review(self, request, queryset):
        queryset.update(status='UNDER_REVIEW', reviewed_at=None)

    mark_under_review.short_description = 'Mark selected applications as under review'

    def approve_application(self, request, queryset):
        queryset.update(status='APPROVED', reviewed_at=None)

    approve_application.short_description = 'Approve selected applications'

    def reject_application(self, request, queryset):
        queryset.update(status='REJECTED', reviewed_at=None)

    reject_application.short_description = 'Reject selected applications'


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'make', 'model', 'year', 'vehicle_type')
    search_fields = ('registration_number', 'make', 'model')


@admin.register(DriverDocument)
class DriverDocumentAdmin(admin.ModelAdmin):
    list_display = ('application', 'document_type', 'uploaded_at', 'verification_status')
    list_filter = ('verification_status', 'document_type')


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'document_type', 'uploaded_at', 'verification_status')
    list_filter = ('verification_status', 'document_type')
