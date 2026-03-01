from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, MaintenanceLog

class CustomCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'role')

class MaintenanceLogForm(forms.ModelForm):
    class Meta:
        model = MaintenanceLog
        fields = ['service_date', 'description', 'cost']
        widgets = {
            'service_date': forms.DateInput(attrs={'type': 'date'}),
        }