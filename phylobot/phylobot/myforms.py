from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from phylobot.models import *

class UserForm(UserCreationForm):
    #password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2',)

class UserProfileForm(forms.ModelForm):
    website = forms.URLField(required=False, help_text="Please enter a website associated with your work")
    
    class Meta:
        model = UserProfile
        fields = ('firstname', 'lastname', 'website', 'picture',)
        