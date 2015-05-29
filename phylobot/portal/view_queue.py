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

    """First check if the job is already running. If it is, then just ignore this request and return"""

    set_last_user_command(job.id, "start")

    if job.checkpoint == -1:
        job.checkpoint = 0
    job.save()


    """ Update S3 """
    job.generate_exe(jumppoint=jumppoint, stoppoint=stoppoint)
    set_job_exe(job.id, job.exe)
    
    """
        to-do: the following file uploads are taking sweet time.
            Maybe we could move the uploads to a separate thread?
    """
    push_jobfile_to_s3(job.id, job.settings.original_aa_file.aaseq_path._get_path() )
    
    """How many taxa and sites in the amino acid sequence collection? -- we'll use this information
        later (in the job daemon) to launch an EC2 instance of the appropriate size."""
    fin = open( job.settings.original_aa_file.aaseq_path._get_path(), "r" )
    ntaxa = 0
    nsites = 0
    lastseq = ""
    for l in fin.xreadlines():
        if l.startswith(">"):
            lastseqlen = lastseq.__len__()
            if nsites > lastseqlen:
                nsites = lastseqlen
            lastseq = ""
            nsites += 1
    fin.close()
    set_ntaxa(job.id, ntaxa)
    set_seqlen(job.id, nsites)
        
    if job.settings.has_codon_data != False:
        push_jobfile_to_s3(job.id, job.settings.original_codon_file.codonseq_path._get_path() )
    if job.settings.constraint_tree_file:
        push_jobfile_to_s3(job.id, job.settings.constraint_tree_file.constrainttree_path._get_path() )
    configfile = job.generate_configfile()
    push_jobfile_to_s3(job.id, configfile)
    setup_slave_startup_script(job.id)
    js = get_job_status(job.id)
    if js == "Stopped" or js == None:
        set_job_status(job.id, "Starting, waiting for cloud resources to spawn")
    # else, the job is already running, so don't override its current status

    """ Add to the SQS """
    sqs_start(job.id)

    """At this point, we're done. We wait for the PhyloBot job daemon
        to read the SQS queue and take action."""
    return

def stop_job(request, job):
    set_last_user_command(job.id, "stop")
    status = get_job_status(job.id)
    if status == "Finished":
        # You can't stop an already stopped job
        return
    set_job_status(job.id, "Stopping, waiting for cloud resources to evaporate")
    sqs_stop(job.id)
    return

def finish_job(request, job):
    """This is a post-success finish state, different from a hard 'stop'.
        Here we request to release the EC2 resources, and leave the job in a "finished" state."""
    sqs_release(job.id)
    return


def trash_job(request, job):
    set_last_user_command(job.id, "trash")
    
    """ Release any EC2 resources"""
    stop_job(request, job)
    
    """Release any S3 resources"""
    clear_all_s3(job.id)
    
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

    


    
