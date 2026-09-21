from typing import Any, cast

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import LoginForm, OTPVerificationForm, SignUpForm
from .models import OTPVerification, User as CustomUser

User = get_user_model()


def send_verification_email(user, otp):
    try:
        send_mail(
            subject='Your TakeOFF verification code',
            message=(
                f'Hi {user.first_name},\n\n'
                f'Your TakeOFF verification code is {otp.code}. '
                'It expires in 5 minutes.\n\n'
                'If you did not create this account, you can ignore this email.'
            ),
            from_email=None,
            recipient_list=[user.email],
        )
        return True
    except (BaseException, Exception):
        return False


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            normalized_email = cleaned['email'].lower()
            try:
                user = User.objects.create_user(
                    username=normalized_email,
                    email=normalized_email,
                    password=cleaned['password1'],
                    first_name=cleaned['first_name'],
                    last_name=cleaned['last_name'],
                    is_active=False,
                )
            except IntegrityError:
                form.add_error('email', 'An account with this email already exists.')
                return render(request, 'auth/signup.html', {'form': form})

            user_obj = cast(CustomUser, user)
            user_obj.phone_number = cleaned['phone_number']
            user_obj.save(update_fields=['phone_number'])

            otp = OTPVerification.generate_for_user(user)
            email_sent = send_verification_email(user, otp)
            request.session['pending_user_id'] = user.pk
            if email_sent:
                messages.success(request, 'Your account was created. Please verify your OTP code.')
            else:
                messages.warning(
                    request,
                    'Your account was created, but the verification email could not be sent. Please request a new code from the next screen.'
                )
            return redirect('verify_otp')
    else:
        form = SignUpForm()
    return render(request, 'auth/signup.html', {'form': form})


def verify_otp_view(request):
    pending_user_id = request.session.get('pending_user_id')
    if not pending_user_id:
        return redirect('signup')

    user = User.objects.filter(id=pending_user_id).first()
    if not user:
        return redirect('signup')

    latest_otp = OTPVerification.objects.filter(user=user).order_by('-created_at').first()
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            submitted_code = form.cleaned_data['otp_code']
            if latest_otp and latest_otp.is_valid and latest_otp.code == submitted_code:
                latest_otp.verified_at = timezone.now()
                latest_otp.save(update_fields=['verified_at'])
                user.is_active = True
                user.save(update_fields=['is_active'])
                request.session.pop('pending_user_id', None)
                login(request, user)
                messages.success(request, 'Your account has been verified.')
                return redirect('dashboard')
            if latest_otp and latest_otp.expires_at < timezone.now():
                messages.error(request, 'This verification code has expired. Please request a new code.')
            else:
                messages.error(request, 'Invalid verification code.')
    else:
        form = OTPVerificationForm()

    return render(request, 'auth/verify_otp.html', {'form': form, 'user': user})


def resend_otp(request):
    pending_user_id = request.session.get('pending_user_id')
    if not pending_user_id:
        return redirect('signup')

    user = User.objects.filter(id=pending_user_id).first()
    if not user:
        return redirect('signup')

    OTPVerification.generate_for_user(user)
    otp = OTPVerification.objects.filter(user=user).order_by('-created_at').first()
    if send_verification_email(user, otp):
        messages.info(request, 'A new verification code has been sent.')
    else:
        messages.warning(request, 'A new verification code was generated, but the email could not be sent right now.')
    return redirect('verify_otp')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                otp = OTPVerification.generate_for_user(user)
                if send_verification_email(user, otp):
                    messages.info(request, 'Your account is not verified. We sent a new OTP to your email.')
                else:
                    messages.warning(request, 'Your account is not verified. A new verification code was generated, but the email could not be sent right now.')
                request.session['pending_user_id'] = user.pk
                return redirect('verify_otp')

            login(request, user)
            messages.success(request, 'Welcome back to TakeOFF.')
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('landing_page')


@login_required
def dashboard_redirect(request):
    return redirect('dashboard')
