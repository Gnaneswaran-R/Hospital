from django.db import models
from django.contrib.auth.models import User


class Doctor(models.Model):
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('on_leave', 'On Leave'),
    ]

    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    speciality = models.CharField(max_length=100)
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    appointment_start = models.TimeField()
    appointment_end = models.TimeField()
    consultation_slots = models.PositiveIntegerField(help_text='Number of slots per day')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'Dr. {self.name} — {self.department}'


class DoctorProfile(models.Model):
    """Links a Django User account to a Doctor record for doctor portal login."""
    user   = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    doctor = models.OneToOneField(Doctor, on_delete=models.CASCADE, related_name='profile')

    def __str__(self):
        return f'{self.user.username} → Dr. {self.doctor.name}'


class DoctorSlot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_present = models.BooleanField(default=True)
    max_bookings = models.PositiveIntegerField(default=1, help_text='Max patients allowed in this slot')

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f'Dr. {self.doctor.name} | {self.date} | {self.start_time} - {self.end_time}'

    def booked_count(self):
        # Only ACCEPTED appointments consume a slot; pending/rejected don't block it
        return self.appointments.filter(status=Appointment.STATUS_ACCEPTED).count()

    def is_full(self):
        return self.booked_count() >= self.max_bookings


class Appointment(models.Model):
    STATUS_PENDING  = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING,  'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    # patient info (merged from old Patient model)
    patient_name   = models.CharField(max_length=100)
    patient_age    = models.PositiveIntegerField(null=True, blank=True)
    patient_gender = models.CharField(max_length=10, blank=True)
    patient_phone  = models.CharField(max_length=15)
    patient_email  = models.EmailField(blank=True, null=True)
    patient_address = models.TextField(blank=True, null=True)
    disease        = models.CharField(max_length=200, blank=True)
    doctor         = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    slot           = models.ForeignKey(DoctorSlot, on_delete=models.CASCADE, related_name='appointments')
    notes          = models.TextField(blank=True, null=True)
    status         = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    booked_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-booked_at']
        constraints = [
            models.UniqueConstraint(
                fields=['slot', 'patient_phone'],
                name='unique_slot_per_phone'
            )
        ]

    def __str__(self):
        return f'{self.patient_name} → Dr. {self.doctor.name} | {self.slot.date}'


class Patient(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=30)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=10)
    email = models.EmailField(max_length=254, blank=True, null=True)
    address = models.TextField()
    disease = models.CharField(max_length=200)
    assigned_doctor = models.ForeignKey(
        Doctor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registered_patients',
        help_text='Auto-assigned based on disease/speciality'
    )
    preferred_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    @property
    def accepted(self):
        return self.status == self.STATUS_ACCEPTED

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
