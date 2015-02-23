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

def get_queue_status():
    the_q = JobQueue.objects.all()
    n = 0
    if the_q.__len__() > 0:
        the_q = the_q[0]
        n = len( the_q.jobs.all() )
    #
    # to-do: this following code is a hack demo
    # fix it so that the reported status is based on
    # ETAs of queued jobs.
    #
    if n > 3:
        return "heavy"
    if n > 2:
        return "medium"
    else:
        return "low"

def checkpoint_to_pdone(checkpoint):
    """Translates the checkpoint into a % complete """
    return 100.0 * checkpoint/7.0

def update_running_job(job):
    """Check on a job that is supposedly running. Is it really running?
    If so, has it passed any checkpoints? If it's not running, did it error?"""
    
    print "\n. view_queue.py 39 - updating running job", job.id, job.settings.name
    
    #
    # Try to read the log.txt from the active running job.
    #
    if job.path:
        if os.path.exists(job.path):
            logpath = job.path + "/log.txt"
            errpath = job.path + "/logerr.txt"
            # Get the last line of the log file from the ASR pipeline
            if os.path.exists(logpath):
                fin = open(logpath, "r")
                lines = fin.readlines()
                if lines.__len__() > 0:
                    (checkpoint, note) = parse_asr_log_line( lines[ lines.__len__()-1 ] )
                    job.checkpoint = checkpoint
                    job.p_done = checkpoint_to_pdone(checkpoint)
                    job.note = note
                    job.save()
                fin.close()
            
            # If the error file has content, then we're in an error situation
            if os.path.exists(errpath):
                fin = open(errpath, "r")
                lines = fin.readlines()
                if lines.__len__() > 0:
                    (checkpoint, note) = parse_asr_log_line( lines[0] )
                    new_status = JobStatus.objects.get(short="error")
                    job.checkpoint = checkpoint
                    job.p_done = checkpoint_to_pdone(checkpoint)
                    job.status = new_status
                    job.note = lines[0]
                    job.save()
                fin.close()
            
            if False == os.path.exists(logpath) and False == os.path.exists(errpath):
                # This is a clear error condition because the log and error log
                # don't exist, but the job status is "running"
                new_status = JobStatus.objects.get(short="error")
                job.status = new_status
                job.save()
            
            print "view_queue.py 54 - job.note = ", job.note.__str__()               

    print "view_queue.py 74 - ", checkpoint, job.status.short
    
    if checkpoint >= 100 and job.status.short == "running":
        # Then the job is finished.
        print "view_queue.py 76 - finishing job", job.id
        job.p_done = 100.0
        finish_job(job)
        return
    
    if job.status.short == "running":
        if checkpoint:
            if checkpoint < 100:
                # OK, so what's going on?
                # The job is supposedly running, but not yet finished.
                # Let's check the process:
                try:
                    unpickled_popen = loads(job.pickled_popen)
                    if not unpickled_popen:
                        # The Popen object doesn't exist.
                        print "view_queue.py 95"
                        new_status = JobStatus.objects.get(short="error")
                        job.status = new_status
                        job.save()
                        return
                    elif unpickled_popen.poll() != 0:
                        # The job has a return code.
                        # zero means stopped with success.
                        print "view_queue.py 221"
                        new_status = JobStatus.objects.get(short="error")
                        job.status = new_status
                        job.save()
                        return

                except TypeError:
                    # This is a situation in which the running job's process isn't running.
                    # We need to restart the job
                    print "view_queue.py 224"
                    #continue_job(job)
    
    # At this point, if the job status is still running, then the job probably
    # is running!



def parse_asr_log_line(line):
    checkpoint = float( line.split()[0] )
    contents = line.split("\t")[1]
    contents.strip()
    return (checkpoint, contents)

def enqueue_job(request, job):    
    """This method assumes that the job has been validated, and can, safely, be launched."""
    the_q = JobQueue.objects.all()[0]
    
    # First determine if the job is already in the queue.
    inq = ["started", "running", "queued"]
    if job.status.short in inq:
        print "I can't launch a job that is already launched. ", job.settings.name, job.id
        return

    new_status = JobStatus.objects.get(short="queued")
    
    # get the shell command to run:
    job.generate_exe()
    
    # Now the job is ready. Add it to the queue. . .
    new_qop = QueueOp(job=job, 
                     queue=the_q,
                     timestamp=datetime.datetime.now(),
                     opcode=1,
                     note = "Added to queue.")
    new_qop.save()
    job.status = new_status
    job.note = None
    job.checkpoint = None
    job.p_done = 0.0
    job.save()
    print "\n. Launched the job", job.id, job.settings.name
    print "\n  --> " + job.exe
    
    update_jobqueues() # this method will deal with spawning subprocesses, and etc.


def continue_job(job):
    """Continues running a job that, for whatever reason, was paused or stalled."""
    print "\n. view_queue.py 129 - continuing job", job.id, job.settings.name
    job.generate_exe()
    print "\n. view_queue.py 162 - Continuing job", job.id, job.settings.name, job.exe
    launch_job(job)

def stop_job(request, job):
    if job.status:
        if job.status.short == "done" or job.status.short == "stopped":
            # You can't stop an already stopped job
            return
    
    the_q = JobQueue.objects.all()[0]

    new_status = JobStatus.objects.get(short="stopping")
    job.status = new_status
    job.save()
    
    if job.pickled_popen:
        print "view_queue.py 100 - stopping job", job.id
        # Load the Popen object
        unpickled_popen = loads(job.pickled_popen.__str__())
        # kill the Popen job
        if unpickled_popen.poll() == None:
            try:
                import signal
                unpickled_popen.terminate()
            except OSError:
                pass
        
        # remove the popen object, but only if the job was actually killed
        job.pickled_popen = None
        
    new_status = JobStatus.objects.get(short="stopped")
    job.status = new_status
    job.note = None
    job.checkpoint = None
    job.p_done = 0.0
    job.save()
                    
    # remove the job from the queue
    try:
        the_op = QueueOp.objects.filter(queue=the_q, job=job)
        for op in the_op:
            print "\n. view_queue.py 123 - removing job from the queue", job.id
            the_op.delete()
    except QueueOp.DoesNotExist:
        # this is an error, or the job just isn't in the queue anymore.
        # either way, mission accomplished.
        pass
    
    update_jobqueues() # this method will deal with spawning subprocesses, and etc.


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
            
    #
    # If the job is in the queue, remove it from the queue.
    #
    the_q = JobQueue.objects.all()[0]
    try:
        the_op = QueueOp.objects.get(queue=the_q, job=job)
        print "\n. view_queue.py 80 - removed job ", job.id
        the_op.delete()
    except QueueOp.DoesNotExist:
        pass

    print "view_queue.py 86 - canceling job #", job.id, "owner:", job.owner
    job.delete()


def finish_job(job):
    """Call this method when a job is finished."""
    new_status = JobStatus.objects.get(short="done")
    job.status = new_status
    job.note = None
    job.pickled_popen = None # We don't need to save the Popen object anymore.
    job.save() 

    the_q = JobQueue.objects.all()[0]
    the_op = QueueOp.objects.filter(queue=the_q, job=job)
    the_op.delete()


def update_jobqueues():
    """This is like a 'main' method for managing the job queue."""
    check_all_queues()
    start_next()

def check_all_queues():
    for jq in JobQueue.objects.all():
        for job in jq.jobs.all():
            refresh_job( job )


def refresh_job(job):
    """This is a helper method used in check_all_queues."""
    
    print "\n. update_jobqueue.py 199 - job", job.settings.name, job.id, job.status.short.__str__()
    if job.status.short == "stopped":
        pass
    
    if job.status.short == "stopping":
        # has it finally stopped?
        pass

    if job.status.short == "running":        
        update_running_job(job)

    if job.status.short == "queued":
        pass


def get_next_queued_job():
    """This is a helper method for start_next."""
    # get the oldest enqueue job operation
    qops = QueueOp.objects.filter(opcode=1).order_by("timestamp")
    if qops:
        for q in qops:
            if q.job.status.short == "queued":
                return q.job 
    else:
        return None

def start_next():
    """If no jobs are running, then launch the next-queued job."""

    # get a list of running jobs:
    r = JobStatus.objects.filter(short="running").all()
    if r.__len__() > 0:
        if len( r[0].job_set.all() ) < 1: # get the list of all jobs that are currently running
             # i.e., no jobs are running
            job = get_next_queued_job()
            if job == None:
                return # the queue is empty!
    
            print "\n. Next job to launch:", job.id, job.settings.name
            print " -->", job.path
            print " --> ", job.exe
            launch_job(job)
    else:
        print "The job queue is empty."


def launch_job(job):
    """Creates a process and launches the job into the OS.
    This method assumes that the job has been validated
    AND that the job has a valid exe field.
    """
    #if job.status.short == "running" or job.status.short == "starting":
    #    print "\n. view_queue.py 323 - I can't launch a job that's already started.", job.id, job.settings.name
    #    return
    
    new_status = JobStatus.objects.get(short="running")
    job.status = new_status
    job.save()
    
    #
    # Start the job here:
    #
    os.chdir( job.path )
    #args = ( job.exe.__str__() + " --stop 2").split()
    args = ( job.exe.__str__() ).split()
    # These are good test cases for args.
    #args = ["ls", "-alh"]
    #args = ["sleep", "100"]
    #args = ["ping", "www.bbc.com"]
    print "\n. Starting a new process with the args:", args
    p = subprocess.Popen(args, preexec_fn=os.setsid)
    print "\n. new pid = ", p.pid       
    
    #
    # Save the Popen object, in pickled form, to the database
    #
    job.pickled_popen = dumps(p)
    job.save()
            
    #
    # Now check if the Popen object is okay.
    #
    unpickled_popen = loads(job.pickled_popen)
    if unpickled_popen.poll() != None:
        print "view_queue.py 279 - the Popen object quickly acquired a return code", job.id 
        # if the Popen object has a return value, then
        # either the job finished super fast, or something is wrong:
        update_running_job(job)
    
