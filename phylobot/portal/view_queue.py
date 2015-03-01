from datetime import datetime

from django.conf import settings
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, Context, loader
from django.contrib.auth.decorators import login_required

from portal.models import *
from portal.forms import *
from portal.tools import *

from portal.view_tools import *


def parse_asr_log_line(line):
    checkpoint = float( line.split()[0] )
    contents = line.split("\t")[1]
    contents.strip()
    return (checkpoint, contents)

def enqueue_job(request, job, jumppoint = None, stoppoint = None):    

    """ Update S3 """
    job.generate_exe(jumppoint=jumppoint, stoppoint=stoppoint)
    set_job_exe(job.id, job.exe)
    
    """
        to-do: these file uploads are taking sweet time.
            Maybe we could move the uploads to a separate thread?
    """
    push_jobfile_to_s3(job.id, job.settings.original_aa_file.aaseq_path._get_path() )
    push_jobfile_to_s3(job.id, job.settings.original_codon_file.codonseq_path._get_path() )
    configfile = job.generate_configfile()
    push_jobfile_to_s3(job.id, configfile)
    set_job_status(job.id, "Starting, waiting for cloud resources to spawn")

    """ Add to the SQS """
    sqs_start(job.id)

    #
    # continue here!
    #
    

def dequeue_job(request, job):
    status = get_job_status(jobid)
    if status == "Finished":
        # You can't stop an already stopped job
        return
    set_job_status(jobid, "Stopping, waiting for cloud resources to evaporate")
    sqs_stop(job.id)


def trash_job(request, job):
    if job.settings:
        #
        # Remove anc. comparisons
        #
        if job.settings.anc_comparisons != None:
            for ac in job.settings.anc_comparisons.all():
                ac.delete()
        if job.settings.ancestors != None:
            for a in job.settings.ancestors.all():
                a.delete()
        if job.settings.original_aa_file:
            for t in job.settings.original_aa_file.contents.all():
                t.delete()
            os.system("rm " + job.settings.original_aa_file.aaseq_path.__str__())
            job.settings.original_aa_file.delete()
        if job.settings.original_codon_file:
            for t in job.settings.original_codon_file.contents.all():
                t.delete()
            os.system("rm " + job.settings.original_codon_file.codonseq_path.__str__())
            job.settings.original_codon_file.delete()
        job.settings.delete()
        
        if job.path:
            if os.path.exists(job.path):
                os.system("rm -rf " + job.path)
            
    job.delete()

    


    
