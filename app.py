import os
import sys
import django
from django.conf import settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='django-hospital-management-secret-key-professional',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'silk.middleware.SilkyMiddleware',
        ],
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django.contrib.sessions',
            'django.contrib.staticfiles',
            'silk',
            'hospital',
        ],
        MIGRATION_MODULES={
            'hospital': 'migrations',
        },
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
            }
        },
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
        },
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
            'APP_DIRS': True,
        }],
        STATIC_URL='/static/',
        STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')],
        CELERY_BROKER_URL='redis://127.0.0.1:6379/0',
        CELERY_RESULT_BACKEND='redis://127.0.0.1:6379/0',
    )

from django.apps import AppConfig

class HospitalConfig(AppConfig):
    name = 'hospital'
    label = 'hospital'

sys.modules['hospital'] = sys.modules[__name__]

django.setup()

from django.core.management import execute_from_command_line
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import path, include
from django.db import models
from django.utils import timezone
from celery import Celery

celery_app = Celery('hospital_tasks')

@celery_app.task
def process_patient_billing_task(patient_id, total_amount):
    return f"billing task processed for patient {patient_id} with amount {total_amount}"

class Patient(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=20)
    contact = models.CharField(max_length=50)
    address = models.TextField()
    blood_group = models.CharField(max_length=10)
    emergency_contact = models.CharField(max_length=50)
    allergies = models.TextField(blank=True, default='none')
    insurance_details = models.CharField(max_length=100, blank=True, default='none')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'hospital'

class Disease(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='diseases')
    disease_name = models.CharField(max_length=100)
    diagnosis_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default='active')
    notes = models.TextField(blank=True)

    class Meta:
        app_label = 'hospital'

class Visit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    visit_date = models.DateField()
    doctor_name = models.CharField(max_length=100)
    doctor_specialty = models.CharField(max_length=100)
    reason = models.CharField(max_length=200)
    diagnosis = models.TextField()
    treatment_notes = models.TextField()

    class Meta:
        app_label = 'hospital'

class DoctorAppointment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor_name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100)
    scheduled_date = models.DateTimeField(null=True, blank=True)
    appointment_type = models.CharField(max_length=20, choices=[('previous', 'previous'), ('programmed', 'programmed')])
    status = models.CharField(max_length=50, default='scheduled')

    class Meta:
        app_label = 'hospital'

class Billing(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='bills')
    invoice_number = models.CharField(max_length=50, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'hospital'

    def pending_balance(self):
        return self.total_amount - self.paid_amount

def patient_list_view(request):
    patients = Patient.objects.all().order_by('-created_at')
    return render(request, 'index.html', {'patients': patients})

def patient_detail_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    diseases = patient.diseases.all()
    visits = patient.visits.all().order_by('-visit_date')
    previous_doctors = patient.appointments.filter(appointment_type='previous')
    programmed_doctors = patient.appointments.filter(appointment_type='programmed')
    bills = patient.bills.all().order_by('-created_at')
    
    total_billed = sum([b.total_amount for b in bills]) if bills else 0
    total_paid = sum([b.paid_amount for b in bills]) if bills else 0
    total_pending = total_billed - total_paid

    context = {
        'patient': patient,
        'diseases': diseases,
        'visits': visits,
        'previous_doctors': previous_doctors,
        'programmed_doctors': programmed_doctors,
        'bills': bills,
        'total_billed': total_billed,
        'total_paid': total_paid,
        'total_pending': total_pending,
    }
    return render(request, 'patient_detail.html', context)

def patient_create_view(request):
    if request.method == 'POST':
        patient = Patient.objects.create(
            name=request.POST.get('name', '').strip(),
            age=int(request.POST.get('age', 0)),
            gender=request.POST.get('gender', '').strip(),
            contact=request.POST.get('contact', '').strip(),
            address=request.POST.get('address', '').strip(),
            blood_group=request.POST.get('blood_group', '').strip(),
            emergency_contact=request.POST.get('emergency_contact', '').strip(),
            allergies=request.POST.get('allergies', 'none').strip(),
            insurance_details=request.POST.get('insurance_details', 'none').strip()
        )
        
        disease_name = request.POST.get('disease_name', '').strip()
        if disease_name:
            d_date = request.POST.get('disease_date').strip() or None
            Disease.objects.create(
                patient=patient,
                disease_name=disease_name,
                diagnosis_date=d_date,
                status=request.POST.get('disease_status', 'active'),
                notes=request.POST.get('disease_notes', '')
            )

        doctor_name = request.POST.get('doctor_name', '').strip()
        if doctor_name:
            a_date = request.POST.get('appointment_date').strip() or None
            DoctorAppointment.objects.create(
                patient=patient,
                doctor_name=doctor_name,
                specialty=request.POST.get('doctor_specialty', 'general'),
                scheduled_date=a_date,
                appointment_type=request.POST.get('appointment_type', 'programmed'),
                status='scheduled'
            )

        bill_total = request.POST.get('bill_total')
        if bill_total:
            total_val = float(bill_total)
            paid_val = float(request.POST.get('bill_paid', 0))
            status_val = 'paid' if paid_val >= total_val else 'pending'
            Billing.objects.create(
                patient=patient,
                invoice_number=f"inv-{patient.id}-01",
                total_amount=total_val,
                paid_amount=paid_val,
                payment_status=status_val
            )

        return redirect('patient_detail', pk=patient.pk)

    return render(request, 'patient_form.html')

urlpatterns = [
    path('', patient_list_view, name='patient_list'),
    path('patient/<int:pk>/', patient_detail_view, name='patient_detail'),
    path('patient/new/', patient_create_view, name='patient_create'),
    path('silk/', include('silk.urls', namespace='silk')),
]

if __name__ == '__main__':
    execute_from_command_line(sys.argv)
