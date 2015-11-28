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

def beta_notice(request):
    return render_to_response('beta_notice.html')

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

def handler404(request):
    response = render_to_response('404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response


def handler500(request):
    response = render_to_response('500.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 500
    return response