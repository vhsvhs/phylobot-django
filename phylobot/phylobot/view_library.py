import os
from django import forms
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.template import RequestContext, Context, loader

from phylobot.models import *

def view_library(request, libid):
    """If a completed ancestral library exists whose name or ID is libid, then
        this method will lead to a view into that library."""
    
    print "\n. 4: entered view_library"
    if libid == None:
        print ". no libid was provided."
    print ". libid=", libid
    
    """Does libid exist in our known libraries?"""
    foundit = False
    for anclib in AncestralLibrary.objects.all():
        if anclib.id.__str__() == libid or anclib.shortname == libid:
            print "I found the library:", libid
            foundit = True
    
    if foundit == False:
        print "\n. I cannot find any ancestral libraries that match your query."
    
    
    # a hack, for now, to just return the user to the main front page.
    return HttpResponseRedirect('/')


