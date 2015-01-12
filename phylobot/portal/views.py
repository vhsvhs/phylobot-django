"""
From the Django tutorials:
Each view is responsible for doing one of two things: returning 
an HttpResponse object containing the content for the requested 
page, or raising an exception such as Http404. The rest is up to you."
"""
from portal.view_tools import *
from portal.view_queue import *

def portal_process_request(request, library=None):
    print "views.py 21 - library = ", library
    
    # Is there a publicly-available project named 'library'
    
    for j in Job.objects.all():
        if j.settings.name == library:
            print "views.py 17 - ", j.id, j.settings.name
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
    #print request.user
    
    # One method:
    #t = loader.get_template('portal/index.html')
    #c = RequestContext(request)
    #return HttpResponse(t.render(c))
    
    # test - can we access the username here?
    # print "32:", request.user
    
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
            stop_job( request, this_job ) 
        if action == "start":
            jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=jobid)[0]
            if this_job.validate():
                enqueue_job( request, this_job )
            else:
                print "I couldn't launch the job:", this_job.name, this_job.id
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
        elif not job.status:
            continue 
        my_jobs.append( job )
        
    #
    # Generate a list of the last X jobs (for all users) in the queue.
    #
    the_q = JobQueue.objects.all()
    q_jobs = []
    if the_q.__len__() > 0:
        for job in the_q.jobs.all():
            if job.status.id > 0: # only jobs that are enqueued or running
                q_jobs.append( job )
    
    #
    # Generate a list of jobs that are complete for user
    #
    my_libraries = []
    if JobStatus.objects.all().__len__() > 0:
        r = JobStatus.objects.get(short="done")
        for job in Job.objects.filter(owner=request.user, status=r):
            my_libraries.append( job )
    
    update_jobqueues()
    
    q_status = get_queue_status()
    
    context_dict = {'jobs':my_jobs,
                    'qjobs':q_jobs,
                    'libraries':my_libraries,
                    'q_status':q_status
                    }
    
    # Another, better, method:
    return render(request, 'portal/index.html', context_dict)
        