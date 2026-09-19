from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset.html', success_url='/forgot-password/done/'), name='password_reset'),
    path('forgot-password/done/', auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html', success_url='/login/'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), name='password_reset_complete'),
]
