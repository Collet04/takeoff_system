from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class DriverProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='driver_profile')
    first_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    alternative_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    residential_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class DriverApplication(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_UNDER_REVIEW = 'UNDER_REVIEW'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_UNDER_REVIEW, 'Under Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    application_reference = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    identity_document_type = models.CharField(max_length=30, blank=True)
    identity_document_number = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    identity_document_file = models.FileField(upload_to='identity_documents/', blank=True, null=True)

    @property
    def progress_steps(self):
        profile = getattr(self.driver, 'driver_profile', None)
        vehicle = getattr(self, 'vehicle', None)
        driver_documents = getattr(self, 'driver_documents', None)
        docs = driver_documents.count() if driver_documents is not None else 0
        vehicle_docs = vehicle.documents.count() if vehicle else 0

        completed = 0
        if profile and profile.first_name:
            completed += 1
        if self.identity_document_type:
            completed += 1
        if vehicle and vehicle.vehicle_type:
            completed += 1
        if docs > 0:
            completed += 1
        if vehicle_docs > 0:
            completed += 1
        if self.status in [self.STATUS_SUBMITTED, self.STATUS_UNDER_REVIEW, self.STATUS_APPROVED, self.STATUS_REJECTED]:
            completed += 1
        return completed

    def clean(self):
        if self.identity_document_type and self.issue_date and self.expiry_date and self.expiry_date < self.issue_date:
            raise ValidationError('Expiry date cannot be earlier than issue date.')

    def __str__(self):
        return self.application_reference


class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('Motorcycle', 'Motorcycle'),
        ('Sedan', 'Sedan'),
        ('Hatchback', 'Hatchback'),
        ('Pickup', 'Pickup'),
        ('Van', 'Van'),
        ('Truck', 'Truck'),
        ('Other', 'Other'),
    ]

    application = models.OneToOneField(DriverApplication, on_delete=models.CASCADE, related_name='vehicle')
    vehicle_type = models.CharField(max_length=30, choices=VEHICLE_TYPE_CHOICES)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    colour = models.CharField(max_length=50)
    registration_number = models.CharField(max_length=50)
    vin_chassis_number = models.CharField(max_length=100)
    max_cargo_capacity = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.make} {self.model}'


class DriverDocument(models.Model):
    DOCUMENT_TYPES = [
        ('Driver\'s Licence', "Driver's Licence"),
        ('Proof of Address', 'Proof of Address'),
        ('Driver Clearance', 'Driver Clearance/Background Document'),
        ('Additional Supporting Document', 'Additional Supporting Document'),
    ]

    application = models.ForeignKey(DriverApplication, on_delete=models.CASCADE, related_name='driver_documents')
    document_type = models.CharField(max_length=100, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='driver_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=20, default='PENDING')
    review_notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['application', 'document_type'],
                name='unique_driver_document_type_per_application',
            )
        ]

    def __str__(self):
        return f'{self.application.application_reference} - {self.document_type}'


class VehicleDocument(models.Model):
    DOCUMENT_TYPES = [
        ('Vehicle Registration', 'Vehicle Registration'),
        ('Vehicle Insurance', 'Vehicle Insurance'),
        ('Vehicle Inspection', 'Vehicle Inspection/Roadworthiness'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=100, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='vehicle_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=20, default='PENDING')
    review_notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['vehicle', 'document_type'],
                name='unique_vehicle_document_type_per_vehicle',
            )
        ]

    def __str__(self):
        return f'{self.vehicle.registration_number} - {self.document_type}'


class ApplicationReview(models.Model):
    application = models.OneToOneField(DriverApplication, on_delete=models.CASCADE, related_name='review_status')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(default=timezone.now)
    decision = models.CharField(max_length=20, choices=[('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.application.application_reference} review'
