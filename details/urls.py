from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/register/', views.register_view, name='register'),
    path('register/', views.add_patient, name='add_patient'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<int:pk>/accept/', views.accept_patient, name='accept_patient'),
    path('patients/<int:pk>/reject/', views.reject_patient, name='reject_patient'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:pk>/edit/', views.edit_patient, name='edit_patient'),
    path('patients/<int:pk>/delete/', views.delete_patient, name='delete_patient'),
    path('doctors/', views.doctors_dashboard, name='doctors_dashboard'),
    path('doctors/<int:pk>/delete/', views.delete_doctor, name='delete_doctor'),
    path('doctors/<int:pk>/edit/', views.edit_doctor, name='edit_doctor'),
    path('doctors/<int:pk>/availability/', views.doctor_availability, name='doctor_availability'),
    path('slots/<int:pk>/edit/', views.edit_slot, name='edit_slot'),
    path('slots/<int:pk>/delete/', views.delete_slot, name='delete_slot'),
    path('book/', views.book_appointment, name='book_appointment'),
    path('book/confirmation/<int:pk>/', views.appointment_confirmation, name='appointment_confirmation'),
    path('ajax/doctors/', views.ajax_doctors_by_speciality, name='ajax_doctors_by_speciality'),
    path('ajax/slots/', views.ajax_slots_by_doctor, name='ajax_slots_by_doctor'),
    path('ajax/doctor-state/', views.ajax_doctor_state, name='ajax_doctor_state'),
    path('ajax/dashboard-stats/', views.ajax_dashboard_stats, name='ajax_dashboard_stats'),
    path('sse/doctor-updates/', views.sse_doctor_updates, name='sse_doctor_updates'),
    # Doctor portal
    path('portal/', views.doctor_portal, name='doctor_portal'),
    path('portal/patients/<int:pk>/', views.doctor_patient_detail, name='doctor_patient_detail'),
    path('portal/patients/<int:pk>/accept/', views.doctor_accept_patient, name='doctor_accept_patient'),
    path('portal/patients/<int:pk>/reject/', views.doctor_reject_patient, name='doctor_reject_patient'),
    path('portal/patients/<int:pk>/delete/', views.doctor_delete_patient, name='doctor_delete_patient'),
]
