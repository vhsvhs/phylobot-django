from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from phylobot.models import *

class UserForm(UserCreationForm):
    #password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name')



    