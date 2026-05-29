import os
import sys
import django
from datetime import date, time, timedelta

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from details.models import Doctor, DoctorSlot

print("--- Generating Slots for All Doctors ---")

today = date.today()
slot_times = [
    (time(9, 0), time(10, 0)),
    (time(10, 0), time(11, 0)),
    (time(11, 0), time(12, 0)),
    (time(14, 0), time(15, 0)),
    (time(15, 0), time(16, 0)),
]

total_slots_created = 0

# Retrieve all doctors from the live database
doctors = Doctor.objects.all()

# Generate slots for the next 15 days (including today)
num_days = 15
max_date = today + timedelta(days=num_days - 1)

print(f"Generating/maintaining slots from {today} to {max_date} (15 days)...")

# Clean up any slots beyond the next 15 days to save space and restore performance
deleted_count, _ = DoctorSlot.objects.filter(date__gt=max_date).delete()
if deleted_count > 0:
    print(f"Removed {deleted_count} stale future slots beyond {max_date}.")

for doctor in doctors:
    print(f"Processing slots for: Dr. {doctor.name} ({doctor.speciality})")
    
    # Iterate for each day in the 15-day range
    for day_offset in range(num_days):
        slot_date = today + timedelta(days=day_offset)
        
        # Check if doctor is on leave on this slot_date
        has_leave = doctor.leaves.filter(start_date__lte=slot_date, end_date__gte=slot_date).exists()
        is_present = False if has_leave else True
        
        # Create 5 slots for this day
        for start_t, end_t in slot_times:
            # Avoid duplicate slot times
            slot, created = DoctorSlot.objects.get_or_create(
                doctor=doctor,
                date=slot_date,
                start_time=start_t,
                end_time=end_t,
                defaults={
                    'is_present': is_present,
                    'max_bookings': 5,
                }
            )
            if created:
                total_slots_created += 1


print(f"\nSuccessfully generated {total_slots_created} new slots. The database now contains slots only up to {max_date} (15 days).")
