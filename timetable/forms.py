from django import forms
from .models import ActualTimetable


class ActualTimetableForm(forms.ModelForm):
    """
    Used when a teacher fills or edits a single slot.
    """
    class Meta:
        model  = ActualTimetable
        fields = ['subject', 'room', 'group', 'time_slot', 'comment']
        widgets = {
            'subject':   forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
            }),
            'room':      forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
            }),
            'group':     forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
            }),
            'time_slot': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': '08:00–09:30',
            }),
            'comment':   forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows':  2,
                'placeholder': 'Optional note...',
            }),
        }


class SlotConfirmForm(forms.Form):
    """Simple confirm — no fields needed, just a POST action."""
    pass


class ReportSubmitForm(forms.Form):
    """
    Teacher submits a week as a report to dekan.
    Optionally picks which dekan to send it to.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    dekan = forms.ModelChoiceField(
        queryset=None,
        empty_label='— Select dekan —',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class':       'form-control form-control-sm',
            'rows':        2,
            'placeholder': 'Optional note to dekan...',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['dekan'].queryset = User.objects.filter(
            role='dekan', is_active=True
        ) 


class ReportReviewForm(forms.Form):
    ACTION_CHOICES = [
        ('approved', 'Approve'),
        ('rejected', 'Reject'),
    ]
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
    note = forms.CharField(
        label='Note to teacher',
        required=False,
        widget=forms.Textarea(attrs={
            'class':       'form-control form-control-sm',
            'rows':        3,
            'placeholder': 'Optional feedback or reason for rejection...',
        })
    )  