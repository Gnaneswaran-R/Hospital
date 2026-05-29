from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Patient, Doctor, DoctorSlot

class PatientDashboardTest(TestCase):
    def setUp(self):
        # Create a staff user to access the dashboard
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpassword',
            is_staff=True
        )
        self.client = Client()

        # Create a doctor
        self.doctor = Doctor.objects.create(
            name='Test Doctor',
            department='Cardiology',
            speciality='Cardiologist',
            availability='available',
            appointment_start='09:00:00',
            appointment_end='17:00:00',
            consultation_slots=5
        )

        # Create a slot for the doctor
        self.slot = DoctorSlot.objects.create(
            doctor=self.doctor,
            date='2026-05-26',
            start_time='09:30:00',
            end_time='10:30:00',
            is_present=True,
            max_bookings=3
        )

        # Create a patient with preferred_time
        self.patient = Patient.objects.create(
            name='John Doe',
            age='0',
            gender='male',
            phone='1234567890',
            email='john@example.com',
            address='123 Main St',
            disease='Hypertension',
            assigned_doctor=self.doctor,
            preferred_date='2026-05-26',
            preferred_time='09:30 AM - 10:30 AM',
            status=Patient.STATUS_PENDING
        )

    def test_patient_fields(self):
        # Verify preferred_time and other fields are correctly saved and queryable
        p = Patient.objects.get(id=self.patient.id)
        self.assertEqual(p.preferred_time, '09:30 AM - 10:30 AM')
        self.assertEqual(p.preferred_date.strftime('%Y-%m-%d'), '2026-05-26')

    def test_dashboard_loading(self):
        # Log in the admin user
        self.client.login(username='admin', password='adminpassword')
        
        # Access dashboard
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')

    def test_ajax_available_times(self):
        # Request available times for Hypertension (maps to Cardiologist) on the slot date
        response = self.client.get(reverse('ajax_available_times'), {
            'disease': 'Hypertension',
            'date': '2026-05-26'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('times', data)
        self.assertEqual(len(data['times']), 1)
        self.assertEqual(data['times'][0]['value'], '09:30 AM - 10:30 AM')


from .models import DoctorLeave, Appointment

class DoctorLeaveTest(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(
            name='Leave Doctor',
            department='Cardiology',
            speciality='Cardiologist',
            availability='available',
            appointment_start='09:00:00',
            appointment_end='17:00:00',
            consultation_slots=5
        )
        self.user = User.objects.create_user(
            username='doctoruser',
            password='doctorpassword'
        )
        from .models import DoctorProfile
        DoctorProfile.objects.create(user=self.user, doctor=self.doctor)
        self.client = Client()

        # Create slots
        self.slot1 = DoctorSlot.objects.create(
            doctor=self.doctor,
            date='2026-06-01',
            start_time='09:00:00',
            end_time='10:00:00',
            is_present=True
        )
        self.slot2 = DoctorSlot.objects.create(
            doctor=self.doctor,
            date='2026-06-02',
            start_time='09:00:00',
            end_time='10:00:00',
            is_present=True
        )

    def test_apply_and_cancel_leave(self):
        # Log in the doctor
        self.client.login(username='doctoruser', password='doctorpassword')

        # Apply for 2 days leave starting 2026-06-01 to 2026-06-02
        response = self.client.post(reverse('doctor_apply_leave'), {
            'start_date': '2026-06-01',
            'end_date': '2026-06-02',
            'reason': 'Vacation'
        })
        self.assertEqual(response.status_code, 302)

        # Verify DoctorLeave is created
        self.assertEqual(DoctorLeave.objects.filter(doctor=self.doctor).count(), 1)
        leave = DoctorLeave.objects.get(doctor=self.doctor)
        self.assertEqual(leave.duration, 2)

        # Verify slots are deactivated
        self.slot1.refresh_from_db()
        self.slot2.refresh_from_db()
        self.assertFalse(self.slot1.is_present)
        self.assertFalse(self.slot2.is_present)

        # Cancel the leave
        response = self.client.post(reverse('doctor_cancel_leave', kwargs={'pk': leave.pk}))
        self.assertEqual(response.status_code, 302)

        # Verify DoctorLeave is deleted
        self.assertEqual(DoctorLeave.objects.filter(doctor=self.doctor).count(), 0)

        # Verify slots are restored to active
        self.slot1.refresh_from_db()
        self.slot2.refresh_from_db()
        self.assertTrue(self.slot1.is_present)
        self.assertTrue(self.slot2.is_present)

    def test_apply_and_cancel_slot_leave(self):
        # Log in the doctor
        self.client.login(username='doctoruser', password='doctorpassword')

        # Create an appointment in slot1
        appt = Appointment.objects.create(
            patient_name='Alice Smith',
            patient_phone='1234567890',
            doctor=self.doctor,
            slot=self.slot1,
            status=Appointment.STATUS_ACCEPTED
        )

        # Apply slot-specific leave on slot1
        response = self.client.post(reverse('doctor_apply_slot_leave', kwargs={'pk': self.slot1.pk}))
        self.assertEqual(response.status_code, 302)

        # Verify slot1 is deactivated but slot2 is still active (not affected)
        self.slot1.refresh_from_db()
        self.slot2.refresh_from_db()
        self.assertFalse(self.slot1.is_present)
        self.assertTrue(self.slot2.is_present)

        # Verify the appointment is cancelled
        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.STATUS_CANCELLED)

        # Reactivate slot1
        response = self.client.post(reverse('doctor_reactivate_slot', kwargs={'pk': self.slot1.pk}))
        self.assertEqual(response.status_code, 302)

        # Verify slot1 is active again
        self.slot1.refresh_from_db()
        self.assertTrue(self.slot1.is_present)




