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

from aws_tools import *

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps
    
def get_mr_seqfile(request):
    lastjob = get_mr_job(request)
    return lastjob.settings.original_aa_file
    
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
        if o.settings == None:
            continue
        if o.settings.name == None or o.settings.original_aa_file == None:
            o.settings.delete()
            o.delete()

def is_valid_fasta(path):
    """This method checks if the FASTA file located at 'path' is a valid FASTA format.
        If there are formatting problems, this method will attempt to fix them (i.e., /r line breaks
        instead of \n line break. If the problems cannot be fixed, then this message will
        return an error.
        
        At the end of checking, this message returns the tuple (flag, message), 
        where flag can be True/False and message is an error message (i.e. a string) if flag==False."""

    msg = None    
    if os.path.exists(path) == False or path == None:
        msg = "An error occurred when uploading your file. Please try again."
        return (False, msg)

    display_path = path.split("/")[ path.split("/").__len__()-1 ]    
    fin = open(path, "r")
    firstchar = None
    lines = fin.readlines()
    fin.close()

    

    cleanlines = []
    for l in lines:    
        #"""Change \r line breaks to \n line breaks"""
        #l = re.sub("\r", "\n", l)
        tokens = l.split()
        for t in tokens:
            """Strip indels"""
            if False == t.startswith(">"):
                t = re.sub(" ", "", t)
                t = re.sub("-", "", t)
            cleanlines.append(t)
        
    
    """Check for correct line breaks -- problems can occur in the FASTA file
        if it was created in Word, or rich text."""
    if cleanlines.__len__() < 3:
        msg = "Something is wrong with your FASTA file. It doesn't appear to contain enough lines. Check your line breaks. Did you create this FASTA file in Word, or some other rich text editor?"
        return (False, msg)
        
    count_seqs = 0
    for l in cleanlines:
        if l.startswith(">"):
            count_seqs += 1
    if count_seqs < 3:
        msg = "Your FASTA file appears to contain two or fewer sequences, and PhyloBot needs at least three sequences. If you think your file contains more sequences, please check the line breaks. If you saved your FASTA file from Microsoft Word, for example, the line breaks may be incorrect."
        return (False, msg)
    
    
    """At this point, the FASTA looks okay. Let's write the clean lines over the saved file."""
    print "116:", path
    fout = open(path, "w")
    for l in cleanlines:
        fout.write(l + "\n")
    fout.close()

    return (True, None)

    