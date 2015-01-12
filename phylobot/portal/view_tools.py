from datetime import datetime
import random, subprocess

from django.conf import settings
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, Context, loader
from django.contrib.auth.decorators import login_required

from portal.models import *
from portal.forms import *
from portal.tools import *

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps
    
def get_mr_seqfile(request):
    lastjob = get_mr_job(request)
    return lastjob.settings.rawseqfile
    
    """Returns the most-recently modified sequence file."""
    # Get the file that was most recently uploaded
    files = SeqFile.objects.filter(owner=request.user)
    newestfile = None
    for f in files:
        if newestfile == None:
            newestfile = f
        elif newestfile.timestamp_uploaded < f.timestamp_uploaded:
            newestfile = f
    return newestfile

def get_mr_genefamily(request):
    lastjob = get_mr_job(request)
    return lastjob.settings.genefamily
    
    """Returns the most-recently modified gene family."""
    genefams = GeneFamily.objects.filter(owner=request.user)
    last_genefam = None
    for g in genefams:
        if last_genefam == None:
            last_genefam = g
        elif last_genefam.last_modified < g.last_modified:
            last_genefam = g  
    return last_genefam

def get_mr_job(request):
    """Returns the most-recently modified gene family."""
    jobs = Job.objects.filter(owner=request.user)
    last_job = None
    for j in jobs:
        if last_job == None:
            last_job = j
        elif last_job.last_modified < j.last_modified:
            last_job = j  
    return last_job

def kill_orphan_jobs(request):
    """Remove any jobs that were started to be composed, but not completed."""
    orphans = Job.objects.filter(owner=request.user)
    for o in orphans:
        if o.settings.name == None or o.settings.rawseqfile == None:
            o.settings.delete()
            o.delete()

def is_valid_fasta(path):
    if os.path.exists(path) == False:
        return False
    fin = open(path, "r")
    firstchar = None
    for l in fin.xreadlines():
        if l.__len__() > 1:
            if firstchar == None:
                if l[0] == ">":
                    return True
                firstchar = l[0]
    return False

def log(message):
    print message
    