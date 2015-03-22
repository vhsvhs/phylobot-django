"""
From the Django tutorials:
Each view is responsible for doing one of two things: returning 
an HttpResponse object containing the content for the requested 
page, or raising an exception such as Http404. The rest is up to you."
"""
from portal.view_tools import *
from portal.view_queue import *
from phylobot import models as phylobotmodels

def portal_process_request(request, library=None):    
    for j in Job.objects.all():
        if j.settings.name == library:
            return HttpResponseRedirect('/static/media/' + j.id + '/HTML/index.html')
    return portal_main_page(request)


@login_required
def portal_main_page(request):
    """
    The login_required decorator does the following:
    If the user isn't logged in, redirect to /accounts/login/, passing 
    current URL path in the query string as next, for example: 
    /accounts/login/?next=/polls/3/.
    If users are authenticated, direct them to the main page. Otherwise, take
    them to the login page.
    """

    #
    # Some housekeeping to perform before showing the portal
    #
    kill_orphan_jobs(request)

    #
    # Process Input
    #
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == "status":
            jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=jobid)            
            return HttpResponseRedirect('/portal/status/' + jobid)
        if action == "edit":
            jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=jobid)            
            return HttpResponseRedirect('/portal/compose/' + jobid)
        if action == "remove":
            jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=jobid)[0]
            trash_job(request, this_job)            
        if action == "stop":
            jobid = request.POST.get( 'jobid' )
            this_job = Job.objects.filter(owner=request.user, id=jobid)[0]
            dequeue_job( request, this_job ) 
        if action == "start":
            jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=jobid)[0]
            if this_job.validate():
                enqueue_job( request, this_job )
            else:
                print >> sys.stderr, "I couldn't launch the job:" + this_job.name + " " + this_job.id.__str__()
    context_dict = {}
    

    
    #
    # Generate a list of jobs that belong to user
    #
    my_jobs = []
    for job in Job.objects.filter(owner=request.user):

        # The idea of these if blocks is to prevent malformed/orphaned
        # jobs from getting displayed.
        if not job.settings:
            continue
        elif not job.settings.name:
            continue
        

        checkpoint = float( get_aws_checkpoint(job.id) )

        job.p_done = 100.0 * float(checkpoint)/9.0
        job.save()
        
        finished_library_id = None
        if checkpoint > 8:
            alib = phylobotmodels.AncestralLibrary.objects.get_or_create(shortname=job.settings.name)[0]
            finished_library_id = alib.id.__str__()
        my_jobs.append( (job, finished_library_id ) )    

    context_dict = {'jobs':my_jobs}
    
    # Another, better, method:
    return render(request, 'portal/index.html', context_dict)
        