import os
from django import forms
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.template import RequestContext, Context, loader

def view_library(request, libid):
    print "\n. 4: entered view_library"
    if libid == None:
        print ". no libid was provided."
    print ". libid=", libid
    
    
    # a hack, for now, to just return the user to the main front page.
    return HttpResponseRedirect('/')