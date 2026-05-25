from django.contrib import admin
from .models import Patient, Doctor, DoctorProfile, DoctorSlot, Appointment


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'doctor')
    list_select_related = ('user', 'doctor')
    autocomplete_fields = []

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Patient)
admin.site.register(Doctor)
admin.site.register(DoctorSlot)
admin.site.register(Appointment)
