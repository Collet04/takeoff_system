from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin/applications/', views.admin_driver_applications_view, name='admin_driver_applications'),
    path('onboarding/personal/', views.personal_details_view, name='personal_details'),
    path('onboarding/identity/', views.identity_verification_view, name='identity_verification'),
    path('onboarding/vehicle/', views.vehicle_details_view, name='vehicle_details'),
    path('onboarding/driver-documents/', views.driver_documents_view, name='driver_documents'),
    path('onboarding/vehicle-documents/', views.vehicle_documents_view, name='vehicle_documents'),
    path('onboarding/review/', views.review_application_view, name='review_application'),
    path('onboarding/submit/', views.submit_application, name='submit_application'),
    path('application/status/', views.application_status_view, name='application_status'),
    path('application/success/', views.application_success_view, name='application_success'),
]
