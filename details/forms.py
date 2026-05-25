from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Patient, Doctor, DoctorSlot, Appointment


class DoctorForm(forms.ModelForm):
    SPECIALITY_CHOICES = [
        ('', 'Select Speciality'),
        ('Cancer Specialist', 'Cancer Specialist'),
        ('Cardiologist', 'Cardiologist'),
        ('Neurologist', 'Neurologist'),
        ('Orthopedic Surgeon', 'Orthopedic Surgeon'),
        ('Dermatologist', 'Dermatologist'),
        ('Pediatrician', 'Pediatrician'),
        ('Psychiatrist', 'Psychiatrist'),
        ('Endocrinologist', 'Endocrinologist'),
        ('Gastroenterologist', 'Gastroenterologist'),
        ('Pulmonologist', 'Pulmonologist'),
        ('Nephrologist', 'Nephrologist'),
        ('Ophthalmologist', 'Ophthalmologist'),
        ('ENT Specialist', 'ENT Specialist'),
        ('General Physician', 'General Physician'),
        ('Other', 'Other'),
    ]

    speciality = forms.ChoiceField(
        choices=SPECIALITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Doctor
        fields = ['name', 'department', 'speciality', 'availability', 'appointment_start', 'appointment_end', 'consultation_slots']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dr. John Smith'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cardiology'}),
            'availability': forms.Select(attrs={'class': 'form-select'}),
            'appointment_start': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'appointment_end': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'consultation_slots': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10'}),
        }


class DoctorExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'})
    )


class DoctorAvailabilityForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['availability']
        widgets = {
            'availability': forms.Select(attrs={'class': 'form-select'}),
        }


class DoctorSlotForm(forms.ModelForm):
    max_bookings = forms.IntegerField(
        min_value=1,
        initial=1,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'e.g. 5'}),
    )

    class Meta:
        model = DoctorSlot
        fields = ['date', 'start_time', 'end_time', 'is_present', 'max_bookings']
        widgets = {
            'date':         forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time':   forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time':     forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'is_present':   forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_max_bookings(self):
        value = self.cleaned_data.get('max_bookings')
        if not value or value < 1:
            return 1
        return value

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('Start time must be before end time.')
        return cleaned_data

class AppointmentForm(forms.ModelForm):
    GENDER_CHOICES = [('', 'Select Gender'), ('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    DISEASE_CHOICES = [
        ('', 'Select a disease'),
        ('Diabetes', 'Diabetes'), ('Hypertension', 'Hypertension'), ('Asthma', 'Asthma'),
        ('Heart Disease', 'Heart Disease'), ('Tuberculosis', 'Tuberculosis'), ('Cancer', 'Cancer'),
        ('Lung Cancer', 'Lung Cancer'), ('Breast Cancer', 'Breast Cancer'),
        ('Kidney Disease', 'Kidney Disease'), ('Liver Disease', 'Liver Disease'),
        ('Arthritis', 'Arthritis'), ('Thyroid Disorder', 'Thyroid Disorder'), ('Anemia', 'Anemia'),
        ('Dengue', 'Dengue'), ('Malaria', 'Malaria'), ('Typhoid', 'Typhoid'),
        ('Pneumonia', 'Pneumonia'), ('Migraine', 'Migraine'), ('Epilepsy', 'Epilepsy'),
        ('Depression', 'Depression'), ('Other', 'Other'),
    ]

    patient_gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    disease        = forms.ChoiceField(choices=DISEASE_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Appointment
        fields = ['patient_name', 'patient_age', 'patient_gender', 'patient_phone',
                  'patient_email', 'patient_address', 'disease', 'notes']
        widgets = {
            'patient_name':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'patient_age':     forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age'}),
            'patient_phone':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9876543210'}),
            'patient_email':   forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'patient_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Address'}),
            'notes':           forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Symptoms or notes (optional)'}),
        }


class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'yourname@example.com',
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class PatientForm(forms.ModelForm):
    DISEASE_CHOICES = [
        ('', 'Select a disease'),
        ('Diabetes', 'Diabetes'),
        ('Hypertension', 'Hypertension'),
        ('Asthma', 'Asthma'),
        ('Heart Disease', 'Heart Disease'),
        ('Tuberculosis', 'Tuberculosis'),
        ('Cancer', 'Cancer'),
        ('Lung Cancer', 'Lung Cancer'),
        ('Breast Cancer', 'Breast Cancer'),
        ('Kidney Disease', 'Kidney Disease'),
        ('Liver Disease', 'Liver Disease'),
        ('Arthritis', 'Arthritis'),
        ('Thyroid Disorder', 'Thyroid Disorder'),
        ('Anemia', 'Anemia'),
        ('Dengue', 'Dengue'),
        ('Malaria', 'Malaria'),
        ('Typhoid', 'Typhoid'),
        ('Pneumonia', 'Pneumonia'),
        ('Migraine', 'Migraine'),
        ('Epilepsy', 'Epilepsy'),
        ('Depression', 'Depression'),
        ('Skin Disease', 'Skin Disease'),
        ('Eczema', 'Eczema'),
        ('Psoriasis', 'Psoriasis'),
        ('Acne', 'Acne'),
        ('Other', 'Other'),
    ]

    disease = forms.ChoiceField(
        choices=DISEASE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = Patient
        fields = [
            'name',
            'age',
            'gender',
            'phone',
            'email',
            'address',
            'disease',
            'preferred_date',
            'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '34'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '9876543210'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'patient@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '123 Main Street'}),
            'preferred_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Additional symptoms or notes'}),
        }
