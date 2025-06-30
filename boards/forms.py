from django import forms
from .models import Task, List

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'due_date': forms.DateInput(attrs={'type': 'date'})
        }

class ListForm(forms.ModelForm):
    class Meta:
        model = List
        fields = ['name']