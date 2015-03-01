import os
from django import forms
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.template import RequestContext, Context, loader
from phylobot.myforms import *

def main_page(request):
    return render_to_response('index.html')

def contact(request):
    return render_to_response('contact.html')

def blog(request):
    return render_to_response('blog.html')

def about(request):
    return render_to_response('about.html')

def logout_page(request):
    """
    Log users out and re-direct them to the main page.
    """
    logout(request)
    return HttpResponseRedirect('/')

def examples(request):
    return render_to_response('examples.html')

def overview(request):
    return render_to_response('learnmore.html')

def register(request):
    # POST method 1:
    """
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            return HttpResponseRedirect("/")
    """
    # POST method 2:
    context = RequestContext(request)

    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    registered = False
    
    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserForm(data=request.POST)

    
        # If the two forms are valid...
        if user_form.is_valid():
            # Save the user's form data to the database.
            user = user_form.save()

            print user

            # Depricated:
            # user.password is already encrypted. If you call set_password,
            # then you'll effectively encrypt the encrypted password.
            # when the user attempts to login, their password won't work.
            #
            # Now we hash the password with the set_password method.
            # Once hashed, we can update the user object.
            #user.set_password(user.password)
            
            
            user.save()

            if False == os.path.exists(settings.MEDIA_ROOT):
                os.system("mkdir " + settings.MEDIA_ROOT)


            # Update our variable to tell the template registration was successful.
            registered = True

        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            print user_form.errors
    
    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        user_form = UserForm()

    # Render the template depending on the context.
    return render_to_response(
            'registration/register.html',
            {'user_form': user_form, 'registered': registered}, context)