from typing import Any, cast

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

from .models import DriverApplication, DriverDocument, DriverProfile, Vehicle, VehicleDocument


def is_admin_user(user):
    return bool(user and (user.is_staff or user.is_superuser))


def get_user_driver_profile(user):
    try:
        return user.driver_profile
    except DriverProfile.DoesNotExist:
        return None


def get_application_vehicle(application):
    try:
        return application.vehicle
    except Vehicle.DoesNotExist:
        return None


STEP_SEQUENCE = [
    {'key': 'account', 'label': 'Account', 'url_name': 'dashboard'},
    {'key': 'personal_details', 'label': 'Personal', 'url_name': 'personal_details'},
    {'key': 'identity_verification', 'label': 'Identity', 'url_name': 'identity_verification'},
    {'key': 'vehicle_details', 'label': 'Vehicle', 'url_name': 'vehicle_details'},
    {'key': 'driver_documents', 'label': 'Driver Documents', 'url_name': 'driver_documents'},
    {'key': 'vehicle_documents', 'label': 'Vehicle Documents', 'url_name': 'vehicle_documents'},
    {'key': 'review_application', 'label': 'Review', 'url_name': 'review_application'},
]


def get_driver_documents(application):
    application_obj = cast(Any, application)
    related = cast(Any, application_obj).driver_documents
    return list(cast(Any, related).all())


def get_vehicle_documents(vehicle):
    vehicle_obj = cast(Any, vehicle)
    related = cast(Any, vehicle_obj).documents
    return list(cast(Any, related).all())


def get_application_step_status(application, user):
    profile = get_user_driver_profile(user)
    vehicle = get_application_vehicle(application)
    driver_documents = get_driver_documents(application)
    vehicle_documents = get_vehicle_documents(vehicle) if vehicle else []

    return {
        'account': True,
        'personal_details': bool(profile and profile.first_name and profile.last_name),
        'identity_verification': bool(application.identity_document_type and application.identity_document_number),
        'vehicle_details': bool(vehicle and vehicle.vehicle_type),
        'driver_documents': bool(driver_documents),
        'vehicle_documents': bool(vehicle_documents),
        'review_application': application.status in [
            DriverApplication.STATUS_SUBMITTED,
            DriverApplication.STATUS_UNDER_REVIEW,
            DriverApplication.STATUS_APPROVED,
            DriverApplication.STATUS_REJECTED,
        ],
    }


def build_step_navigation(current_step):
    current_index = next((index for index, step in enumerate(STEP_SEQUENCE) if step['key'] == current_step), 0)
    steps = []

    for step in STEP_SEQUENCE:
        status = get_application_step_status(get_application_for_user(step['url_name'] if False else None), None) if False else {}
        steps.append({
            'key': step['key'],
            'label': step['label'],
            'url_name': step['url_name'],
            'completed': False,
        })

    return {
        'step_map': STEP_SEQUENCE,
        'current_step': current_step,
        'previous_step': STEP_SEQUENCE[current_index - 1] if current_index > 0 else None,
        'next_step': STEP_SEQUENCE[current_index + 1] if current_index < len(STEP_SEQUENCE) - 1 else None,
    }


# Pylance can misread Django reverse relations as missing; these local aliases keep the
# access pattern explicit without changing runtime behavior.
# These are intentionally lightweight type hints for the reverse relations used below.
DriverDocuments = Any
VehicleRelation = Any
DocumentQuerySet = Any
VehicleDocumentQuerySet = Any

# Keep the model reverse relations explicit for static analysis.
ApplicationDriverDocuments = Any
VehicleDocumentsRelation = Any


@login_required
def dashboard(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    profile = get_user_driver_profile(request.user)
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
        'step_status': get_application_step_status(application, request.user),
        'step_map': STEP_SEQUENCE,
    }
    return render(request, 'driver_app/dashboard.html', context)


@login_required
def personal_details_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    profile = get_user_driver_profile(request.user)
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

    step_status = get_application_step_status(application, request.user)
    current_step = 'personal_details'
    step_navigation = {
        'step_map': [
            {'key': 'account', 'label': 'Account', 'url_name': 'dashboard', 'completed': True},
            {'key': 'personal_details', 'label': 'Personal', 'url_name': 'personal_details', 'completed': step_status['personal_details']},
            {'key': 'identity_verification', 'label': 'Identity', 'url_name': 'identity_verification', 'completed': step_status['identity_verification']},
            {'key': 'vehicle_details', 'label': 'Vehicle', 'url_name': 'vehicle_details', 'completed': step_status['vehicle_details']},
            {'key': 'driver_documents', 'label': 'Driver Documents', 'url_name': 'driver_documents', 'completed': step_status['driver_documents']},
            {'key': 'vehicle_documents', 'label': 'Vehicle Documents', 'url_name': 'vehicle_documents', 'completed': step_status['vehicle_documents']},
            {'key': 'review_application', 'label': 'Review', 'url_name': 'review_application', 'completed': step_status['review_application']},
        ],
        'current_step': current_step,
        'previous_step': None,
        'next_step': {'key': 'identity_verification', 'url_name': 'identity_verification'},
    }
    return render(request, 'driver_app/personal_details.html', {'form': form, 'application': application, 'step_status': step_status, 'step_map': step_navigation['step_map'], 'current_step': current_step, 'previous_step': None, 'next_step': step_navigation['next_step']})


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
    step_status = get_application_step_status(application, request.user)
    current_step = 'identity_verification'
    step_navigation = {
        'step_map': [
            {'key': 'account', 'label': 'Account', 'url_name': 'dashboard', 'completed': True},
            {'key': 'personal_details', 'label': 'Personal', 'url_name': 'personal_details', 'completed': step_status['personal_details']},
            {'key': 'identity_verification', 'label': 'Identity', 'url_name': 'identity_verification', 'completed': step_status['identity_verification']},
            {'key': 'vehicle_details', 'label': 'Vehicle', 'url_name': 'vehicle_details', 'completed': step_status['vehicle_details']},
            {'key': 'driver_documents', 'label': 'Driver Documents', 'url_name': 'driver_documents', 'completed': step_status['driver_documents']},
            {'key': 'vehicle_documents', 'label': 'Vehicle Documents', 'url_name': 'vehicle_documents', 'completed': step_status['vehicle_documents']},
            {'key': 'review_application', 'label': 'Review', 'url_name': 'review_application', 'completed': step_status['review_application']},
        ],
        'previous_step': {'key': 'personal_details', 'url_name': 'personal_details'},
        'next_step': {'key': 'vehicle_details', 'url_name': 'vehicle_details'},
    }
    return render(request, 'driver_app/identity_verification.html', {'form': form, 'application': application, 'step_status': step_status, 'step_map': step_navigation['step_map'], 'current_step': current_step, 'previous_step': step_navigation['previous_step'], 'next_step': step_navigation['next_step']})


@login_required
def vehicle_details_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    vehicle = get_application_vehicle(application)
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
    step_status = get_application_step_status(application, request.user)
    current_step = 'vehicle_details'
    step_navigation = {
        'step_map': [
            {'key': 'account', 'label': 'Account', 'url_name': 'dashboard', 'completed': True},
            {'key': 'personal_details', 'label': 'Personal', 'url_name': 'personal_details', 'completed': step_status['personal_details']},
            {'key': 'identity_verification', 'label': 'Identity', 'url_name': 'identity_verification', 'completed': step_status['identity_verification']},
            {'key': 'vehicle_details', 'label': 'Vehicle', 'url_name': 'vehicle_details', 'completed': step_status['vehicle_details']},
            {'key': 'driver_documents', 'label': 'Driver Documents', 'url_name': 'driver_documents', 'completed': step_status['driver_documents']},
            {'key': 'vehicle_documents', 'label': 'Vehicle Documents', 'url_name': 'vehicle_documents', 'completed': step_status['vehicle_documents']},
            {'key': 'review_application', 'label': 'Review', 'url_name': 'review_application', 'completed': step_status['review_application']},
        ],
        'previous_step': {'key': 'identity_verification', 'url_name': 'identity_verification'},
        'next_step': {'key': 'driver_documents', 'url_name': 'driver_documents'},
    }
    return render(request, 'driver_app/vehicle_details.html', {'form': form, 'application': application, 'step_status': step_status, 'step_map': step_navigation['step_map'], 'current_step': current_step, 'previous_step': step_navigation['previous_step'], 'next_step': step_navigation['next_step']})


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
    step_status = get_application_step_status(application, request.user)
    current_step = 'driver_documents'
    step_navigation = {
        'step_map': [
            {'key': 'account', 'label': 'Account', 'url_name': 'dashboard', 'completed': True},
            {'key': 'personal_details', 'label': 'Personal', 'url_name': 'personal_details', 'completed': step_status['personal_details']},
            {'key': 'identity_verification', 'label': 'Identity', 'url_name': 'identity_verification', 'completed': step_status['identity_verification']},
            {'key': 'vehicle_details', 'label': 'Vehicle', 'url_name': 'vehicle_details', 'completed': step_status['vehicle_details']},
            {'key': 'driver_documents', 'label': 'Driver Documents', 'url_name': 'driver_documents', 'completed': step_status['driver_documents']},
            {'key': 'vehicle_documents', 'label': 'Vehicle Documents', 'url_name': 'vehicle_documents', 'completed': step_status['vehicle_documents']},
            {'key': 'review_application', 'label': 'Review', 'url_name': 'review_application', 'completed': step_status['review_application']},
        ],
        'previous_step': {'key': 'vehicle_details', 'url_name': 'vehicle_details'},
        'next_step': {'key': 'vehicle_documents', 'url_name': 'vehicle_documents'},
    }
    return render(request, 'driver_app/driver_documents.html', {'form': form, 'application': application, 'step_status': step_status, 'step_map': step_navigation['step_map'], 'current_step': current_step, 'previous_step': step_navigation['previous_step'], 'next_step': step_navigation['next_step']})


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
    step_status = get_application_step_status(application, request.user)
    current_step = 'vehicle_documents'
    step_navigation = {
        'step_map': [
            {'key': 'account', 'label': 'Account', 'url_name': 'dashboard', 'completed': True},
            {'key': 'personal_details', 'label': 'Personal', 'url_name': 'personal_details', 'completed': step_status['personal_details']},
            {'key': 'identity_verification', 'label': 'Identity', 'url_name': 'identity_verification', 'completed': step_status['identity_verification']},
            {'key': 'vehicle_details', 'label': 'Vehicle', 'url_name': 'vehicle_details', 'completed': step_status['vehicle_details']},
            {'key': 'driver_documents', 'label': 'Driver Documents', 'url_name': 'driver_documents', 'completed': step_status['driver_documents']},
            {'key': 'vehicle_documents', 'label': 'Vehicle Documents', 'url_name': 'vehicle_documents', 'completed': step_status['vehicle_documents']},
            {'key': 'review_application', 'label': 'Review', 'url_name': 'review_application', 'completed': step_status['review_application']},
        ],
        'previous_step': {'key': 'driver_documents', 'url_name': 'driver_documents'},
        'next_step': {'key': 'review_application', 'url_name': 'review_application'},
    }
    return render(request, 'driver_app/vehicle_documents.html', {'form': form, 'application': application, 'step_status': step_status, 'step_map': step_navigation['step_map'], 'current_step': current_step, 'previous_step': step_navigation['previous_step'], 'next_step': step_navigation['next_step']})


@login_required
def review_application_view(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    profile = get_user_driver_profile(request.user)
    vehicle: VehicleRelation = get_application_vehicle(application)
    documents: DriverDocuments = get_driver_documents(application)
    vehicle_documents = get_vehicle_documents(vehicle) if vehicle else []
    form = ReviewConfirmationForm()
    context = {
        'application': application,
        'profile': profile,
        'vehicle': vehicle,
        'documents': documents,
        'vehicle_documents': vehicle_documents,
        'form': form,
    }
    step_status = get_application_step_status(application, request.user)
    current_step = 'review_application'
    step_navigation = {
        'step_map': [
            {'key': 'account', 'label': 'Account', 'url_name': 'dashboard', 'completed': True},
            {'key': 'personal_details', 'label': 'Personal', 'url_name': 'personal_details', 'completed': step_status['personal_details']},
            {'key': 'identity_verification', 'label': 'Identity', 'url_name': 'identity_verification', 'completed': step_status['identity_verification']},
            {'key': 'vehicle_details', 'label': 'Vehicle', 'url_name': 'vehicle_details', 'completed': step_status['vehicle_details']},
            {'key': 'driver_documents', 'label': 'Driver Documents', 'url_name': 'driver_documents', 'completed': step_status['driver_documents']},
            {'key': 'vehicle_documents', 'label': 'Vehicle Documents', 'url_name': 'vehicle_documents', 'completed': step_status['vehicle_documents']},
            {'key': 'review_application', 'label': 'Review', 'url_name': 'review_application', 'completed': step_status['review_application']},
        ],
        'previous_step': {'key': 'vehicle_documents', 'url_name': 'vehicle_documents'},
        'next_step': None,
    }
    context.update({'step_status': step_status, 'step_map': step_navigation['step_map'], 'current_step': current_step, 'previous_step': step_navigation['previous_step'], 'next_step': step_navigation['next_step']})
    return render(request, 'driver_app/review_application.html', context)


@login_required
def submit_application(request):
    if is_admin_user(request.user):
        return redirect('admin_driver_applications')

    application = get_application_for_user(request.user)
    if request.method == 'POST':
        form = ReviewConfirmationForm(request.POST)
        if form.is_valid():
            driver_docs = cast(Any, getattr(application, 'driver_documents', None))
            vehicle_rel = cast(Any, getattr(application, 'vehicle', None))
            vehicle_docs = cast(Any, getattr(vehicle_rel, 'documents', None)) if vehicle_rel else None

            required_docs = [
                ("Driver's Licence", driver_docs.filter(document_type="Driver's Licence").exists() if driver_docs is not None else False),
                ('Proof of Address', driver_docs.filter(document_type='Proof of Address').exists() if driver_docs is not None else False),
                ('Driver Clearance', driver_docs.filter(document_type='Driver Clearance').exists() if driver_docs is not None else False),
                ('Vehicle Registration', vehicle_docs.filter(document_type='Vehicle Registration').exists() if vehicle_docs is not None else False),
                ('Vehicle Insurance', vehicle_docs.filter(document_type='Vehicle Insurance').exists() if vehicle_docs is not None else False),
                ('Vehicle Inspection', vehicle_docs.filter(document_type='Vehicle Inspection').exists() if vehicle_docs is not None else False),
            ]
            if not all(is_present for _, is_present in required_docs):
                messages.error(request, 'Please upload all required driver and vehicle documents before submitting.')
                return redirect('review_application')
            if not get_user_driver_profile(request.user):
                messages.error(request, 'Please complete your personal details before submitting.')
                return redirect('personal_details')
            if not get_application_vehicle(application):
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

    try:
        send_mail(subject, message, None, [recipient], fail_silently=False)
        return True
    except Exception:
        return False


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
