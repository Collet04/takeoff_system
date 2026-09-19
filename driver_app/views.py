from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone


def admin_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'This page is only available to administrators.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

from .forms import (
    DriverDocumentForm,
    DriverProfileForm,
    IdentityVerificationForm,
    ReviewConfirmationForm,
    VehicleDocumentForm,
    VehicleForm,
)
from typing import Any

from .models import DriverApplication, DriverDocument, DriverProfile, Vehicle, VehicleDocument


def is_admin_user(user):
    return bool(user and (user.is_staff or user.is_superuser))


# Pylance can misread Django reverse relations as missing; these local aliases keep the
# access pattern explicit without changing runtime behavior.
DriverDocuments = Any
VehicleRelation = Any


@login_required
def dashboard(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    profile = getattr(request.user, 'driver_profile', None)
    application = DriverApplication.objects.filter(driver=request.user).order_by('-created_at').first()
    if not application:
        application = DriverApplication.objects.create(driver=request.user, application_reference=generate_application_reference())
    if profile:
        profile.email = request.user.email or profile.email
        profile.phone_number = request.user.phone_number or profile.phone_number
        profile.save(update_fields=['email', 'phone_number'])

    context = {
        'profile': profile,
        'application': application,
        'progress': application.progress_steps if application else 0,
    }
    return render(request, 'driver_app/dashboard.html', context)


@login_required
def personal_details_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    profile = getattr(request.user, 'driver_profile', None)
    if request.method == 'POST':
        form = DriverProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile_obj = form.save(commit=False)
            profile_obj.user = request.user
            profile_obj.email = request.user.email
            profile_obj.phone_number = request.user.phone_number
            profile_obj.save()
            application.status = DriverApplication.STATUS_IN_PROGRESS
            application.save(update_fields=['status'])
            messages.success(request, 'Personal details saved.')
            return redirect('identity_verification')
    else:
        form = DriverProfileForm(instance=profile)

    return render(request, 'driver_app/personal_details.html', {'form': form, 'application': application})


@login_required
def identity_verification_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    if request.method == 'POST':
        form = IdentityVerificationForm(request.POST, request.FILES, instance=application)
        if form.is_valid():
            application = form.save(commit=False)
            application.status = DriverApplication.STATUS_IN_PROGRESS
            application.save()
            messages.success(request, 'Identity verification saved.')
            return redirect('vehicle_details')
    else:
        form = IdentityVerificationForm(instance=application)
    return render(request, 'driver_app/identity_verification.html', {'form': form, 'application': application})


@login_required
def vehicle_details_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    vehicle = getattr(application, 'vehicle', None)
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            vehicle_obj = form.save(commit=False)
            vehicle_obj.application = application
            vehicle_obj.save()
            application.status = DriverApplication.STATUS_IN_PROGRESS
            application.save(update_fields=['status'])
            messages.success(request, 'Vehicle details saved.')
            return redirect('driver_documents')
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, 'driver_app/vehicle_details.html', {'form': form, 'application': application})


@login_required
def driver_documents_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    if request.method == 'POST':
        form = DriverDocumentForm(request.POST, request.FILES, application=application)
        if form.is_valid():
            saved_any = False
            for document_type, field_name in DriverDocumentForm.DOCUMENT_FIELDS:
                uploaded_file = request.FILES.get(field_name)
                if uploaded_file:
                    DriverDocument.objects.create(
                        application=application,
                        document_type=document_type,
                        file=uploaded_file,
                    )
                    saved_any = True
            if saved_any:
                messages.success(request, 'Driver documents uploaded.')
                return redirect('vehicle_documents')
            messages.error(request, 'Please select at least one document to upload.')
    else:
        form = DriverDocumentForm(application=application)
    return render(request, 'driver_app/driver_documents.html', {'form': form, 'application': application})


@login_required
def vehicle_documents_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    vehicle = getattr(application, 'vehicle', None)
    if not vehicle:
        messages.error(request, 'Please complete vehicle details first.')
        return redirect('vehicle_details')

    if request.method == 'POST':
        form = VehicleDocumentForm(request.POST, request.FILES, vehicle=vehicle)
        if form.is_valid():
            saved_any = False
            for document_type, field_name in VehicleDocumentForm.DOCUMENT_FIELDS:
                uploaded_file = request.FILES.get(field_name)
                if uploaded_file:
                    VehicleDocument.objects.create(
                        vehicle=vehicle,
                        document_type=document_type,
                        file=uploaded_file,
                    )
                    saved_any = True
            if saved_any:
                messages.success(request, 'Vehicle documents uploaded.')
                return redirect('review_application')
            messages.error(request, 'Please select at least one document to upload.')
    else:
        form = VehicleDocumentForm(vehicle=vehicle)
    return render(request, 'driver_app/vehicle_documents.html', {'form': form, 'application': application})


@login_required
def review_application_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    profile = getattr(request.user, 'driver_profile', None)
    vehicle: VehicleRelation = getattr(application, 'vehicle', None)
    documents: DriverDocuments = list(application.driver_documents.all())
    vehicle_documents = list(vehicle.documents.all()) if vehicle else []
    form = ReviewConfirmationForm()
    context = {
        'application': application,
        'profile': profile,
        'vehicle': vehicle,
        'documents': documents,
        'vehicle_documents': vehicle_documents,
        'form': form,
    }
    return render(request, 'driver_app/review_application.html', context)


@login_required
def submit_application(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    if request.method == 'POST':
        form = ReviewConfirmationForm(request.POST)
        if form.is_valid():
            required_docs = [
                ("Driver's Licence", application.driver_documents.filter(document_type="Driver's Licence").exists()),
                ('Proof of Address', application.driver_documents.filter(document_type='Proof of Address').exists()),
                ('Driver Clearance', application.driver_documents.filter(document_type='Driver Clearance').exists()),
                ('Vehicle Registration', application.vehicle.documents.filter(document_type='Vehicle Registration').exists() if application.vehicle else False),
                ('Vehicle Insurance', application.vehicle.documents.filter(document_type='Vehicle Insurance').exists() if application.vehicle else False),
                ('Vehicle Inspection', application.vehicle.documents.filter(document_type='Vehicle Inspection').exists() if application.vehicle else False),
            ]
            if not all(is_present for _, is_present in required_docs):
                messages.error(request, 'Please upload all required driver and vehicle documents before submitting.')
                return redirect('review_application')
            if not getattr(request.user, 'driver_profile', None):
                messages.error(request, 'Please complete your personal details before submitting.')
                return redirect('personal_details')
            if not getattr(application, 'vehicle', None):
                messages.error(request, 'Please complete vehicle details before submitting.')
                return redirect('vehicle_details')
            application.status = DriverApplication.STATUS_SUBMITTED
            application.submitted_at = timezone.now()
            application.save(update_fields=['status', 'submitted_at'])
            messages.success(request, 'Your application has been submitted successfully.')
            return redirect('application_success')

    messages.error(request, 'Please confirm the application information before submitting.')
    return redirect('review_application')


def send_application_decision_email(application, decision, notes=''):
    recipient = getattr(application.driver, 'email', None)
    if not recipient:
        return False

    driver_name = getattr(application.driver, 'first_name', '') or 'Applicant'
    reference = application.application_reference
    note_text = (notes or '').strip()

    if decision == DriverApplication.STATUS_APPROVED:
        subject = f'Your TakeOFF application has been approved - {reference}'
        message = (
            f'Dear {driver_name},\n\n'
            'Congratulations! Your TakeOFF driver application has been approved.\n'
            f'Application reference: {reference}\n\n'
            f'{note_text or "We are pleased to confirm that your documents and profile meet our requirements."}\n\n'
            'Welcome aboard and thank you for choosing TakeOFF.\n\n'
            'Kind regards,\n'
            'TakeOFF Team'
        )
    else:
        subject = f'Your TakeOFF application update - {reference}'
        message = (
            f'Dear {driver_name},\n\n'
            'We regret to inform you that your TakeOFF driver application was not approved at this time.\n'
            f'Application reference: {reference}\n\n'
            f'{note_text or "After reviewing your uploaded documents and profile, we are unable to proceed with approval at this stage."}\n\n'
            'Please review the details and you may reapply once the required information is updated.\n\n'
            'Kind regards,\n'
            'TakeOFF Team'
        )

    send_mail(subject, message, None, [recipient], fail_silently=False)
    return True


@admin_required
def admin_driver_applications_view(request):
    applications = DriverApplication.objects.filter(
        status__in=[DriverApplication.STATUS_SUBMITTED, DriverApplication.STATUS_UNDER_REVIEW]
    ).select_related('driver', 'vehicle').prefetch_related('driver_documents', 'vehicle__documents').order_by('-created_at')

    if request.method == 'POST':
        application_id = request.POST.get('application_id')
        decision = request.POST.get('decision')
        notes = (request.POST.get('review_notes') or '').strip()
        application = get_object_or_404(DriverApplication, pk=application_id)

        if decision == 'DELETE':
            applicant = application.driver
            application.delete()
            applicant.delete()
            messages.success(request, f'Applicant {applicant.email} and all related application details were deleted.')
            return redirect('admin_driver_applications')

        if decision not in [DriverApplication.STATUS_APPROVED, DriverApplication.STATUS_REJECTED]:
            messages.error(request, 'Please choose a valid decision.')
            return redirect('admin_driver_applications')

        application.status = decision
        application.reviewed_at = timezone.now()
        application.review_notes = notes
        application.rejection_reason = notes if decision == DriverApplication.STATUS_REJECTED else ''
        application.save(update_fields=['status', 'reviewed_at', 'review_notes', 'rejection_reason'])
        send_application_decision_email(application, decision, notes)
        messages.success(request, f'Application {application.application_reference} was {decision.lower()}.')
        return redirect('admin_driver_applications')

    return render(request, 'driver_app/admin_applications.html', {'applications': applications})


@login_required
def application_status_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')
    application = get_application_for_user(request.user)
    return render(request, 'driver_app/application_status.html', {'application': application})


@login_required
def application_success_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')
    application = get_application_for_user(request.user)
    return render(request, 'driver_app/application_success.html', {'application': application})


def get_application_for_user(user):
    if is_admin_user(user):
        raise PermissionDenied('Administrators do not have applicant records.')
    app = DriverApplication.objects.filter(driver=user).order_by('-created_at').first()
    if not app:
        app = DriverApplication.objects.create(driver=user, application_reference=generate_application_reference())
    return app


def generate_application_reference():
    import random
    return f"TKO-{timezone.now().year}-{random.randint(1, 9999):05d}"
