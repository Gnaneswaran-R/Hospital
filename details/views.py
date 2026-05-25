from django.http import JsonResponse
from urllib.parse import urlencode
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
import openpyxl

from .forms import PatientForm, UserRegistrationForm, DoctorForm, DoctorExcelUploadForm, DoctorAvailabilityForm, DoctorSlotForm, AppointmentForm
from .models import Patient, Doctor, DoctorSlot, Appointment, DoctorProfile


# ── Disease → Speciality mapping ──
DISEASE_SPECIALITY_MAP = {
    'Diabetes':          'Endocrinologist',
    'Hypertension':      'Cardiologist',
    'Asthma':            'Pulmonologist',
    'Heart Disease':     'Cardiologist',
    'Tuberculosis':      'Pulmonologist',
    'Cancer':            'Cancer Specialist',
    'Lung Cancer':       'Cancer Specialist',
    'Breast Cancer':     'Cancer Specialist',
    'Kidney Disease':    'Nephrologist',
    'Liver Disease':     'Gastroenterologist',
    'Arthritis':         'Orthopedic Surgeon',
    'Thyroid Disorder':  'Endocrinologist',
    'Anemia':            'General Physician',
    'Dengue':            'General Physician',
    'Malaria':           'General Physician',
    'Typhoid':           'General Physician',
    'Pneumonia':         'Pulmonologist',
    'Migraine':          'Neurologist',
    'Epilepsy':          'Neurologist',
    'Depression':        'Psychiatrist',
    'Skin Disease':      'Dermatologist',
    'Eczema':            'Dermatologist',
    'Psoriasis':         'Dermatologist',
    'Acne':              'Dermatologist',
    'Other':             'General Physician',
}


def _assign_doctor_for_disease(disease):
    """Return the best available doctor for a given disease, or None."""
    speciality = DISEASE_SPECIALITY_MAP.get(disease, 'General Physician')
    doctor = Doctor.objects.filter(
        speciality__iexact=speciality, availability='available'
    ).first()
    if not doctor:
        # fallback: any available doctor
        doctor = Doctor.objects.filter(availability='available').first()
    return doctor


def _get_doctor_patients(doctor):
    """
    Return all Patient records that belong to this doctor.
    Includes both explicitly assigned patients AND unassigned patients
    whose disease maps to this doctor's speciality.
    """
    from django.db.models import Q
    # diseases that map to this doctor's speciality
    matching_diseases = [
        disease for disease, spec in DISEASE_SPECIALITY_MAP.items()
        if spec == doctor.speciality
    ]
    return Patient.objects.filter(
        Q(assigned_doctor=doctor) |
        Q(assigned_doctor__isnull=True, disease__in=matching_diseases)
    ).distinct()


class StyledLoginView(LoginView):
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        return form


def _is_admin(user):
    return user.is_authenticated and user.is_staff


def _is_doctor(user):
    return user.is_authenticated and hasattr(user, 'doctor_profile')


def home(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard')
    if request.user.is_authenticated and hasattr(request.user, 'doctor_profile'):
        return redirect('doctor_portal')
    return render(request, 'hospital/home.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('add_patient')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account was created. Please sign in to continue.')
            return redirect('login')
        messages.error(request, 'Please correct the issues below.')
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


def add_patient(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.assigned_doctor = _assign_doctor_for_disease(patient.disease)
            patient.save()
            messages.success(request, 'Your registration has been submitted successfully.')
            return redirect('home')
        messages.error(request, 'Please fix the highlighted fields.')
    else:
        form = PatientForm()
    return render(request, 'hospital/register_patient.html', {'form': form})


@user_passes_test(_is_admin, login_url='login')
def dashboard(request):
    from django.utils.timezone import now
    today = now().date()

    patients = Patient.objects.all()
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')
    disease_filter = request.GET.get('disease', '').strip()

    if query:
        patients = patients.filter(name__icontains=query)
    if disease_filter:
        patients = patients.filter(disease__icontains=disease_filter)
    if status_filter in [Patient.STATUS_PENDING, Patient.STATUS_ACCEPTED, Patient.STATUS_REJECTED]:
        patients = patients.filter(status=status_filter)

    total_patients    = Patient.objects.count()
    accepted_patients = Patient.objects.filter(status=Patient.STATUS_ACCEPTED).count()
    rejected_patients = Patient.objects.filter(status=Patient.STATUS_REJECTED).count()
    pending_patients  = Patient.objects.filter(status=Patient.STATUS_PENDING).count()

    paginator = Paginator(patients.order_by('-created_at'), 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    current_query = query_params.urlencode()

    # doctors live panel
    all_doctors = Doctor.objects.all()
    total_doctors     = all_doctors.count()
    available_doctors = all_doctors.filter(availability='available').count()
    on_leave_doctors  = all_doctors.filter(availability='on_leave').count()

    # today's appointments
    todays_appointments = Appointment.objects.filter(
        slot__date=today
    ).select_related('doctor', 'slot').order_by('slot__start_time')

    return render(request, 'hospital/dashboard.html', {
        'patients': page_obj,
        'query': query,
        'status_filter': status_filter,
        'disease_filter': disease_filter,
        'current_query': current_query,
        'page_obj': page_obj,
        'total_patients': total_patients,
        'accepted_patients': accepted_patients,
        'rejected_patients': rejected_patients,
        'pending_patients': pending_patients,
        'all_doctors': all_doctors,
        'total_doctors': total_doctors,
        'available_doctors': available_doctors,
        'on_leave_doctors': on_leave_doctors,
        'todays_appointments': todays_appointments,
        'today': today,
    })


@user_passes_test(_is_admin, login_url='login')
def patient_list(request):
    return redirect('dashboard')


def _send_appointment_email(appointment, accepted=True):
    if not appointment.patient_email:
        return
    status_text = 'Accepted' if accepted else 'Rejected'
    subject = f'Your Appointment has been {status_text} — HospitalCare'
    if accepted:
        message = (
            f'Dear {appointment.patient_name},\n\n'
            f'Your appointment with Dr. {appointment.doctor.name} ({appointment.doctor.speciality}) '
            f'has been ACCEPTED.\n'
            f'Date: {appointment.slot.date}\n'
            f'Time: {appointment.slot.start_time.strftime("%I:%M %p")} – {appointment.slot.end_time.strftime("%I:%M %p")}\n\n'
            'Please arrive 10 minutes early. Contact us if you need to reschedule.\n\n'
            'Best regards,\nHospitalCare Team'
        )
    else:
        message = (
            f'Dear {appointment.patient_name},\n\n'
            f'We regret to inform you that your appointment request with Dr. {appointment.doctor.name} '
            f'has been REJECTED.\n'
            'Please book another slot or contact our support team for assistance.\n\n'
            'Best regards,\nHospitalCare Team'
        )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
              [appointment.patient_email], fail_silently=False)


@user_passes_test(_is_admin, login_url='login')
def doctor_appointments(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    status_filter = request.GET.get('status', 'pending')
    appointments = doctor.appointments.all()
    if status_filter in [Appointment.STATUS_PENDING, Appointment.STATUS_ACCEPTED, Appointment.STATUS_REJECTED]:
        appointments = appointments.filter(status=status_filter)
    return render(request, 'hospital/doctor_appointments.html', {
        'doctor': doctor,
        'appointments': appointments,
        'status_filter': status_filter,
        'pending_count': doctor.appointments.filter(status=Appointment.STATUS_PENDING).count(),
    })


@user_passes_test(_is_admin, login_url='login')
def accept_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        appointment.status = Appointment.STATUS_ACCEPTED
        appointment.save()
        _send_appointment_email(appointment, accepted=True)
        messages.success(request, f'{appointment.patient_name}\'s appointment accepted and notified by email.')
    return redirect('doctor_appointments', pk=appointment.doctor.pk)


@user_passes_test(_is_admin, login_url='login')
def reject_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        appointment.status = Appointment.STATUS_REJECTED
        appointment.save()
        _send_appointment_email(appointment, accepted=False)
        messages.success(request, f'{appointment.patient_name}\'s appointment rejected and notified by email.')
    return redirect('doctor_appointments', pk=appointment.doctor.pk)


@user_passes_test(_is_admin, login_url='login')
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    return render(request, 'hospital/patient_detail.html', {'patient': patient})


@user_passes_test(_is_admin, login_url='login')
def edit_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient details updated successfully.')
            return redirect('dashboard')
        messages.error(request, 'Please fix the highlighted fields.')
    else:
        form = PatientForm(instance=patient)
    return render(request, 'hospital/edit_patient.html', {'form': form, 'patient': patient})


@user_passes_test(_is_admin, login_url='login')
def delete_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        patient.delete()
        messages.success(request, 'Patient record deleted successfully.')
        return redirect('dashboard')
    return render(request, 'hospital/delete_patient.html', {'patient': patient})


def _send_patient_email(patient, accepted=True):
    if not patient.email:
        return
    status_text = 'Accepted' if accepted else 'Rejected'
    subject = f'Your Registration Status: {status_text} — HospitalCare'
    
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    
    template_name = 'hospital/email_accepted.html' if accepted else 'hospital/email_rejected.html'
    html_message = render_to_string(template_name, {'patient': patient})
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [patient.email],
        html_message=html_message,
        fail_silently=False
    )


@user_passes_test(_is_admin, login_url='login')
def accept_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patient.status = Patient.STATUS_ACCEPTED
    patient.save()
    _send_patient_email(patient, accepted=True)
    messages.success(request, f'Patient {patient.name} has been accepted and notified by email.')
    
    next_url = request.POST.get('next') or request.GET.get('next') or 'dashboard'
    return redirect(next_url)


@user_passes_test(_is_admin, login_url='login')
def reject_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patient.status = Patient.STATUS_REJECTED
    patient.save()
    _send_patient_email(patient, accepted=False)
    messages.success(request, f'Patient {patient.name} has been rejected and notified by email.')
    
    next_url = request.POST.get('next') or request.GET.get('next') or 'dashboard'
    return redirect(next_url)


def logout_view(request):
    auth_logout(request)
    return redirect('home')


# ── Doctor Portal ──

@user_passes_test(_is_doctor, login_url='login')
def doctor_portal(request):
    """Doctor's own dashboard — sees assigned patients + unassigned patients matching their speciality."""
    doctor = request.user.doctor_profile.doctor
    patients = _get_doctor_patients(doctor)

    status_filter = request.GET.get('status', 'all')
    query = request.GET.get('q', '').strip()

    if query:
        patients = patients.filter(name__icontains=query)
    if status_filter in [Patient.STATUS_PENDING, Patient.STATUS_ACCEPTED, Patient.STATUS_REJECTED]:
        patients = patients.filter(status=status_filter)

    base_qs  = _get_doctor_patients(doctor)
    total    = base_qs.count()
    pending  = base_qs.filter(status=Patient.STATUS_PENDING).count()
    accepted = base_qs.filter(status=Patient.STATUS_ACCEPTED).count()
    rejected = base_qs.filter(status=Patient.STATUS_REJECTED).count()

    paginator = Paginator(patients.order_by('-created_at'), 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'hospital/doctor_portal.html', {
        'doctor': doctor,
        'patients': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'query': query,
        'total': total,
        'pending': pending,
        'accepted': accepted,
        'rejected': rejected,
    })


@user_passes_test(_is_doctor, login_url='login')
def doctor_accept_patient(request, pk):
    doctor = request.user.doctor_profile.doctor
    patient = get_object_or_404(_get_doctor_patients(doctor), pk=pk)
    if request.method == 'POST':
        patient.assigned_doctor = doctor  # lock assignment on action
        patient.status = Patient.STATUS_ACCEPTED
        patient.save()
        _send_patient_email(patient, accepted=True)
        messages.success(request, f'{patient.name} has been accepted and notified by email.')
    return redirect('doctor_portal')


@user_passes_test(_is_doctor, login_url='login')
def doctor_reject_patient(request, pk):
    doctor = request.user.doctor_profile.doctor
    patient = get_object_or_404(_get_doctor_patients(doctor), pk=pk)
    if request.method == 'POST':
        patient.assigned_doctor = doctor  # lock assignment on action
        patient.status = Patient.STATUS_REJECTED
        patient.save()
        _send_patient_email(patient, accepted=False)
        messages.success(request, f'{patient.name} has been rejected and notified by email.')
    return redirect('doctor_portal')


@user_passes_test(_is_doctor, login_url='login')
def doctor_delete_patient(request, pk):
    doctor = request.user.doctor_profile.doctor
    patient = get_object_or_404(_get_doctor_patients(doctor), pk=pk)
    if request.method == 'POST':
        name = patient.name
        patient.delete()
        messages.success(request, f'Patient record for {name} has been deleted.')
    return redirect('doctor_portal')


@user_passes_test(_is_doctor, login_url='login')
def doctor_patient_detail(request, pk):
    doctor = request.user.doctor_profile.doctor
    patient = get_object_or_404(_get_doctor_patients(doctor), pk=pk)
    return render(request, 'hospital/doctor_patient_detail.html', {
        'patient': patient,
        'doctor': doctor,
    })


@user_passes_test(_is_admin, login_url='login')
def doctors_dashboard(request):
    search = request.GET.get('q', '').strip()
    dept_filter = request.GET.get('department', '').strip()
    avail_filter = request.GET.get('availability', '').strip()

    doctors = Doctor.objects.all()
    if search:
        doctors = doctors.filter(name__icontains=search)
    if dept_filter:
        doctors = doctors.filter(department__icontains=dept_filter)
    if avail_filter:
        doctors = doctors.filter(availability=avail_filter)

    add_form = DoctorForm()
    upload_form = DoctorExcelUploadForm()
    errors = []

    if request.method == 'POST':
        if 'add_doctor' in request.POST:
            add_form = DoctorForm(request.POST)
            if add_form.is_valid():
                add_form.save()
                messages.success(request, 'Doctor added successfully.')
                return redirect('doctors_dashboard')

        elif 'upload_excel' in request.POST:
            upload_form = DoctorExcelUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                excel_file = request.FILES['excel_file']
                try:
                    wb = openpyxl.load_workbook(excel_file)
                    ws = wb.active
                    imported = 0
                    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                        name, department, speciality, availability, appt_start, appt_end, slots = (list(row) + [None]*7)[:7]
                        if not name or not department:
                            errors.append(f'Row {i}: Name and Department are required.')
                            continue
                        availability = availability if availability in ['available', 'unavailable', 'on_leave'] else 'available'
                        Doctor.objects.create(
                            name=str(name).strip(),
                            department=str(department).strip(),
                            speciality=str(speciality).strip() if speciality else '',
                            availability=availability,
                            appointment_start=appt_start or '09:00',
                            appointment_end=appt_end or '17:00',
                            consultation_slots=int(slots) if slots else 10,
                        )
                        imported += 1
                    if imported:
                        messages.success(request, f'{imported} doctor(s) imported successfully.')
                    if errors:
                        for e in errors:
                            messages.warning(request, e)
                except Exception as ex:
                    messages.error(request, f'Failed to read Excel file: {ex}')
                return redirect('doctors_dashboard')

    departments = Doctor.objects.values_list('department', flat=True).distinct()

    return render(request, 'hospital/doctors_dashboard.html', {
        'doctors': doctors,
        'add_form': add_form,
        'upload_form': upload_form,
        'search': search,
        'dept_filter': dept_filter,
        'avail_filter': avail_filter,
        'departments': departments,
        'total_doctors': Doctor.objects.count(),
        'available_doctors': Doctor.objects.filter(availability='available').count(),
        'on_leave_doctors': Doctor.objects.filter(availability='on_leave').count(),
    })


@user_passes_test(_is_admin, login_url='login')
def delete_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        doctor.delete()
        messages.success(request, f'Dr. {doctor.name} has been removed.')
    return redirect('doctors_dashboard')


@user_passes_test(_is_admin, login_url='login')
def edit_doctor(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Doctor updated successfully.')
            return redirect('doctors_dashboard')
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'hospital/edit_doctor.html', {'form': form, 'doctor': doctor})


@user_passes_test(_is_admin, login_url='login')
def doctor_availability(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    slots = doctor.slots.all()
    avail_form = DoctorAvailabilityForm(instance=doctor)
    slot_form = DoctorSlotForm()

    if request.method == 'POST':
        if 'update_availability' in request.POST:
            old_availability = doctor.availability
            avail_form = DoctorAvailabilityForm(request.POST, instance=doctor)
            if avail_form.is_valid():
                avail_form.save()
                # if doctor is now absent/on_leave, deactivate all their slots instantly
                if doctor.availability in ['unavailable', 'on_leave']:
                    doctor.slots.all().update(is_present=False)
                elif doctor.availability == 'available':
                    doctor.slots.all().update(is_present=True)
                messages.success(request, f'Dr. {doctor.name}\'s availability updated.')
                return redirect('doctor_availability', pk=pk)

        elif 'add_slot' in request.POST:
            slot_form = DoctorSlotForm(request.POST)
            if slot_form.is_valid():
                slot = slot_form.save(commit=False)
                slot.doctor = doctor
                slot.save()
                messages.success(request, 'Slot added successfully.')
                return redirect('doctor_availability', pk=pk)
            else:
                messages.error(request, 'Please fix the slot form errors.')

    date_filter = request.GET.get('date', '').strip()
    if date_filter:
        slots = slots.filter(date=date_filter)

    return render(request, 'hospital/doctor_availability.html', {
        'doctor': doctor,
        'slots': slots,
        'avail_form': avail_form,
        'slot_form': slot_form,
        'date_filter': date_filter,
    })


@user_passes_test(_is_admin, login_url='login')
def edit_slot(request, pk):
    slot = get_object_or_404(DoctorSlot, pk=pk)
    doctor = slot.doctor
    if request.method == 'POST':
        form = DoctorSlotForm(request.POST, instance=slot)
        if form.is_valid():
            form.save()
            messages.success(request, 'Slot updated successfully.')
            return redirect('doctor_availability', pk=doctor.pk)
    else:
        form = DoctorSlotForm(instance=slot)
    return render(request, 'hospital/edit_slot.html', {'form': form, 'slot': slot, 'doctor': doctor})


@user_passes_test(_is_admin, login_url='login')
def delete_slot(request, pk):
    slot = get_object_or_404(DoctorSlot, pk=pk)
    doctor_pk = slot.doctor.pk
    if request.method == 'POST':
        slot.delete()
        messages.success(request, 'Slot removed.')
    return redirect('doctor_availability', pk=doctor_pk)


# ── AJAX: full doctor state for real-time sync ──
def ajax_doctor_state(request):
    from django.utils.timezone import now
    today = now().date()
    doctors = Doctor.objects.all().values(
        'id', 'name', 'department', 'speciality', 'availability',
        'appointment_start', 'appointment_end', 'consultation_slots'
    )
    result = []
    for d in doctors:
        slots = DoctorSlot.objects.filter(
            doctor_id=d['id'],
            is_present=True,
            date__gte=today
        ).count() if d['availability'] == 'available' else 0
        result.append({
            **d,
            'appointment_start': d['appointment_start'].strftime('%I:%M %p'),
            'appointment_end':   d['appointment_end'].strftime('%I:%M %p'),
            'active_slots': slots,
        })
    specialities = list(
        Doctor.objects.filter(availability='available')
        .values_list('speciality', flat=True).distinct()
    )
    return JsonResponse({'doctors': result, 'specialities': specialities})


# ── AJAX: dashboard stats (patients + doctor counts) ──
def ajax_dashboard_stats(request):
    return JsonResponse({
        'total_patients':    Patient.objects.count(),
        'accepted_patients': Patient.objects.filter(status=Patient.STATUS_ACCEPTED).count(),
        'rejected_patients': Patient.objects.filter(status=Patient.STATUS_REJECTED).count(),
        'pending_patients':  Patient.objects.filter(status=Patient.STATUS_PENDING).count(),
        'total_doctors':     Doctor.objects.count(),
        'available_doctors': Doctor.objects.filter(availability='available').count(),
        'on_leave_doctors':  Doctor.objects.filter(availability='on_leave').count(),
        'unavailable_doctors': Doctor.objects.filter(availability='unavailable').count(),
    })


# ── SSE: stream doctor updates to connected clients ──
import time as _time
def sse_doctor_updates(request):
    from django.http import StreamingHttpResponse
    from django.utils.timezone import now

    def event_stream():
        last = None
        while True:
            today = now().date()
            doctors_qs = list(
                Doctor.objects.all().values(
                    'id', 'name', 'department', 'speciality',
                    'availability', 'consultation_slots',
                    'appointment_start', 'appointment_end'
                )
            )
            # attach open slot count per doctor
            doctors = []
            for d in doctors_qs:
                slots_qs = DoctorSlot.objects.filter(
                    doctor_id=d['id'], is_present=True, date__gte=today
                ) if d['availability'] == 'available' else []
                open_slots = sum(
                    1 for s in slots_qs
                    if s.appointments.exclude(status=Appointment.STATUS_CANCELLED).count() < s.max_bookings
                )
                doctors.append({
                    **d,
                    'open_slots': open_slots,
                    'has_slots': len(slots_qs) > 0
                })

            specialities = list(
                Doctor.objects.filter(availability='available')
                .values_list('speciality', flat=True).distinct()
            )
            stats = {
                'total_patients':      Patient.objects.count(),
                'accepted_patients':   Patient.objects.filter(status=Patient.STATUS_ACCEPTED).count(),
                'rejected_patients':   Patient.objects.filter(status=Patient.STATUS_REJECTED).count(),
                'pending_patients':    Patient.objects.filter(status=Patient.STATUS_PENDING).count(),
                'total_doctors':       Doctor.objects.count(),
                'available_doctors':   Doctor.objects.filter(availability='available').count(),
                'on_leave_doctors':    Doctor.objects.filter(availability='on_leave').count(),
                'unavailable_doctors': Doctor.objects.filter(availability='unavailable').count(),
            }
            import json
            payload = json.dumps({
                'doctors': doctors,
                'specialities': specialities,
                'stats': stats,
            }, default=str)
            if payload != last:
                last = payload
                yield f'data: {payload}\n\n'
            _time.sleep(5)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# ── AJAX: return doctors filtered by speciality ──
def ajax_doctors_by_speciality(request):
    from django.utils.timezone import now
    today = now().date()
    speciality = request.GET.get('speciality', '').strip()
    doctors = Doctor.objects.filter(
        speciality__iexact=speciality,
        availability='available'
    ).values('id', 'name', 'department', 'availability')
    result = []
    for d in doctors:
        available_slots = DoctorSlot.objects.filter(
            doctor_id=d['id'],
            is_present=True,
            date__gte=today
        )
        # count slots that are not fully booked
        open_slots = sum(
            1 for s in available_slots
            if s.appointments.exclude(status=Appointment.STATUS_CANCELLED).count() < s.max_bookings
        )
        result.append({
            **d,
            'open_slots': open_slots,
            'has_slots': available_slots.exists()
        })
    return JsonResponse({'doctors': result})


# ── AJAX: return active slots for a doctor ──
def ajax_slots_by_doctor(request):
    doctor_id = request.GET.get('doctor_id', '').strip()
    from django.utils.timezone import now
    today = now().date()

    try:
        doctor = Doctor.objects.get(pk=doctor_id)
        if doctor.availability != 'available':
            return JsonResponse({'slots': []})
    except Doctor.DoesNotExist:
        return JsonResponse({'slots': []})

    slots = DoctorSlot.objects.filter(
        doctor_id=doctor_id,
        is_present=True,
        date__gte=today
    )
    data = []
    for s in slots:
        booked = s.appointments.exclude(status=Appointment.STATUS_CANCELLED).count()
        data.append({
            'id':          s.id,
            'date':        s.date.strftime('%b %d, %Y'),
            'start_time':  s.start_time.strftime('%I:%M %p'),
            'end_time':    s.end_time.strftime('%I:%M %p'),
            'booked':      booked,
            'max':         s.max_bookings,
            'is_full':     booked >= s.max_bookings,
            'slots_left':  max(s.max_bookings - booked, 0),
        })
    return JsonResponse({'slots': data})


# ── Patient Appointment Booking ──
def book_appointment(request):
    if request.method == 'POST':
        slot_id   = request.POST.get('slot_id')
        doctor_id = request.POST.get('doctor_id')
        form      = AppointmentForm(request.POST)

        if not slot_id or not doctor_id:
            messages.error(request, 'Please select a doctor and a slot.')
            return render(request, 'hospital/book_appointment.html', {'form': form})

        doctor = get_object_or_404(Doctor, pk=doctor_id)
        slot   = get_object_or_404(DoctorSlot, pk=slot_id)

        # hard guard: reject booking if doctor is absent
        if doctor.availability != 'available' or not slot.is_present:
            messages.error(request, 'This doctor is currently unavailable. Please choose another.')
            return render(request, 'hospital/book_appointment.html', {'form': form})

        # guard: slot fully booked
        if slot.is_full():
            messages.error(request, 'This slot is fully booked. Please choose another slot.')
            return render(request, 'hospital/book_appointment.html', {'form': form})

        # guard: same phone already booked this slot
        phone = request.POST.get('patient_phone', '').strip()
        if Appointment.objects.filter(slot=slot, patient_phone=phone).exclude(status=Appointment.STATUS_CANCELLED).exists():
            messages.error(request, 'You have already booked this slot. Please choose a different slot.')
            return render(request, 'hospital/book_appointment.html', {'form': form})

        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.doctor = doctor
            appointment.slot   = slot
            appointment.save()
            return redirect('appointment_confirmation', pk=appointment.pk)
        else:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'hospital/book_appointment.html', {'form': form})

    else:
        form = AppointmentForm()

    return render(request, 'hospital/book_appointment.html', {'form': form})


def appointment_confirmation(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    return render(request, 'hospital/appointment_confirmation.html', {
        'appointment': appointment
    })
