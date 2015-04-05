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
        jobid = request.POST.get('jobid')
        if jobid == None:
            return
        
        this_job = Job.objects.filter(owner=request.user, id=jobid)
        if request.user.username == "admin":
            this_job = Job.objects.filter(id=jobid)
        this_job = this_job[0]
        
        action = request.POST.get('action')
        if action == "status":
                
            return HttpResponseRedirect('/portal/status/' + jobid)
        if action == "edit":           
            return HttpResponseRedirect('/portal/compose/' + jobid)
        if action == "remove":
            trash_job(request, this_job)            
        if action == "stop":
            stop_job( request, this_job ) 
        if action == "start":
            if this_job.validate():
                enqueue_job( request, this_job )
            else:
                print >> sys.stderr, "I couldn't launch the job:" + this_job.name + " " + this_job.id.__str__()
    context_dict = {}
    

    
    #
    # Generate a list of jobs that belong to user
    #
    my_jobs = []
    show_owner = False
    
    """For a normal user, just show their jobs.
        But for admin, show all jobs"""
    if request.user.username == "admin":
        ij =  Job.objects.all()
        show_owner = True
    else:
        ij =  Job.objects.filter(owner=request.user)
    for job in ij:

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

        

    context_dict = {'jobs':my_jobs,
                    'show_owner':show_owner}
    
    # Another, better, method:
    return render(request, 'portal/index.html', context_dict)


@login_required
def jobstatus(request, jobid):
    job = None
    if jobid:
        jobid = re.sub("/", "", jobid)
        print "102: get status for", jobid
        try:
            job = Job.objects.get(id=jobid)
        except Job.DoesNotExist:
            print "411: job doesn't exist"
            pass
    if job == None:
        job = get_mr_job(request)
        jobid = job.id
        
    context = RequestContext(request)
    
    """this_jobid and this_job are parsed from the POST. They may be None,
        in which case, we'll stick with job and job from the previous lines."""
    this_jobid = None
    this_job = None
    if request.method == 'POST':
        this_jobid = request.POST.get('jobid')
        if this_jobid == None:
            return
        
        this_job = Job.objects.filter(owner=request.user, id=this_jobid)
        if request.user.username == "admin":
            this_job = Job.objects.filter(id=this_jobid)
        this_job = this_job[0]
        
        action = request.POST.get('action')
        print "371:", action
        if action == "edit":            
            return HttpResponseRedirect('/portal/compose/' + this_jobid)
        if action == "remove":
            context_dict = {}
            context_dict['jobname'] = this_job.settings.name
            context_dict['jobid'] = this_job.id
            trash_job(request, this_job)
            return render(request, 'portal/trashed.html', context_dict)            
        if action == "reset":
            reset_job( request, this_job ) 
        if action == "stop":
            stop_job( request, this_job ) 
        if action == "start":
            if this_job.validate():
                enqueue_job( request, this_job )
            else:
                print >> sys.stderr, "I couldn't validate the job: " + this_job.name + " " + this_job.id.__str__()
        if action == "refresh":
            """Default, the rest of this method will do the status refresh"""
            pass
    
    list_of_aa = []
    for aa in job.settings.alignment_algorithms.all():
        list_of_aa.append( aa.name )
    list_of_rm = []
    for rm in job.settings.raxml_models.all():
        list_of_rm.append( rm.name )
    
    if jobid == None:
        if this_jobid != None:
            job = this_job
    
    if job.id == None:
        print >> sys.stderr, "I couldn't process the status request for an unknown job ID"
    
    
    """What was the last button pushed for this job? i.e., start, stop, trash, etc."""
    last_user_command = get_last_user_command(job.id)
    
    selected_aaseqfile = None
    selected_aaseqfile_short = None
    if job.settings.original_aa_file:
        selected_aaseqfile =  settings.STATIC_MEDIA_URL + job.settings.original_aa_file.aaseq_path.__str__()
        selected_aaseqfile_short = selected_aaseqfile.split("/")[ selected_aaseqfile.split("/").__len__()-1 ]
    

    selected_constrainttreefile = None
    selected_constrainttreefile_short = None
    if job.settings.constraint_tree_file:
        selected_constrainttreefile = settings.STATIC_MEDIA_URL +  job.settings.constraint_tree_file.constrainttree_path.__str__()
        selected_constrainttreefile_short = selected_constrainttreefile.split("/")[ selected_constrainttreefile.split("/").__len__()-1 ]

    job_status = get_job_status(job.id)
    checkpoint = float( get_aws_checkpoint(job.id) )
    
    checkpoints = []
    checkpoints.append( (1.1,     "Sequence Alignment") )
    checkpoints.append( (2.7,     "Calculate Alignment Support with ZORRO") )
    checkpoints.append( (3.1,     "ML Phylogeny Inference") )
    checkpoints.append( (5,     "Phylogenetic Support") )
    checkpoints.append( (5.11,     "Ancestral Sequence Reconstruction") )
    checkpoints.append( (8,     "Done") )
    
    finished_library_id = None
    
    job.p_done = 100.0 * float(checkpoint)/8.0
    job.save()
    
    if checkpoint == 8 and job_status == "Finished":
        print "views_compose.py 380 - let's import", job.id
        
        contact_authors_profile = phylobotmodels.UserProfile.objects.get_or_create(user=request.user)[0]
        #print "383:", contact_authors_profile
        contact_authors_profile.save()
        
        alib = phylobotmodels.AncestralLibrary.objects.get_or_create(shortname=job.settings.name)[0]
        #print "384:", alib
        
        relationship = phylobotmodels.AncestralLibrarySourceJob.objects.get_or_create(jobid=job.id, libid=alib.id)[0]
        #print "383:", relationship
        relationship.save()
        
        save_to_path = settings.MEDIA_ROOT + "/anclibs/asr_" + job.id.__str__() + ".db"
        #print "392:", save_to_path
        get_asrdb(job.id, save_to_path)
        
        if False == os.path.exists(save_to_path):
            print "398 - the db save didn't work"
        else:
            print "400 - the db save worked!"
            checkpoint = 9.0
            set_aws_checkpoint(job.id, checkpoint)
        
        alib.dbpath = "anclibs/asr_" + job.id.__str__() + ".db"
        alib.save()
    
    if checkpoint >= 8:
        alib = phylobotmodels.AncestralLibrary.objects.get_or_create(shortname=job.settings.name)[0]
        finished_library_id = alib.id.__str__()
        print "409:", finished_library_id
        #
        #  continue here - get finished_library_id into the template
        #
    
    context_dict = {'job': job, 
                    'job_status': job_status,
                    'last_user_command':last_user_command,
                    'nseqs':job.settings.original_aa_file.contents.count(),
                    'list_of_aa':list_of_aa,
                    'list_of_rm':list_of_rm,
                    'checkpoints':checkpoints,
                    'current_checkpoint':checkpoint,
                    'finished_library_id':finished_library_id,
                    'selected_aaseqfile_short':selected_aaseqfile_short,
                    'selected_aa_seqfile_url':selected_aaseqfile,
                    'constrainttree_seqfile_url':    selected_constrainttreefile,
                    'constrainttree_seqfile_short':  selected_constrainttreefile_short,
                    }
    
    return render(request, 'portal/status.html', context_dict)
     