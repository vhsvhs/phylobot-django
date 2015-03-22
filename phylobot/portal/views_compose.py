from portal.view_tools import *
from portal.view_queue import *

from phylobot import models as phylobotmodels
@login_required
def composenew(request):
    """Creates a new Job object, then redirects to compose1"""
    newjob = Job.objects.create(owner=request.user)
    newjob.checkpoint = -1
    newjob.save()
    return HttpResponseRedirect('/portal/compose1')


@login_required
def edit_job(request, jobid):
    this_job = Job.objects.filter(owner=request.user, id=jobid)
    if this_job:
        this_job = this_job[0]
        this_job.last_modified = datetime.datetime.now()
        this_job.save()
    print "20:", request.method
    return HttpResponseRedirect('/portal/compose1')

@login_required
def compose1(request):
    """Step 1 of the job composer.
    The protocol is that BEFORE calling this function, touch a Job object.
    That job object will then be loaded  upon calling get_mr_job.
    See below for an example.
    """
    
    context = RequestContext(request)    
    this_job = get_mr_job(request)
    error_messages = []
    
    first_time_composing = False
    
    if this_job.settings == None:
        first_time_composing = True
        this_js = JobSetting()
        this_js.save()
        this_job.settings = this_js
        this_job.save()
        
    if request.method == 'POST':                
        aa_seqfileform = AASeqFileForm(request.POST, request.FILES)
        codon_seqfileform = CodonSeqFileForm(request.POST, request.FILES)
        js_form = JobSettingForm(request.POST)
      
        #
        # Deal with the sequence file itself
        #
        aaseqfile = None
        codonseqfile = None
        inputnames = ["aaseq_path", "codonseq_path"]
        for ii in range(0, inputnames.__len__()):
            
            inputname = inputnames[ii]
            if inputname not in request.FILES:
                continue
            filepath = request.FILES[inputname]
            
            seqfile = None
            this_type = None
            if ii == 0: 
                """AA"""
                seqfile = AASeqFile(aaseq_path=filepath)
                this_type = "aa"
            elif ii == 1: 
                """Codons"""
                seqfile = CodonSeqFile(codonseq_path=filepath)
                this_type = "codon"
            seqfile.owner = request.user
            
            #
            # to-do: change these values based on parsing the actual file.
            #
            this_format = "fasta"
            if this_format == "fasta":
                seqfile.format = SeqFileFormat.objects.get_or_create(name=this_format)[0]
                seqfile.save()

            # full path to the uploaded sequence file.
            fullpath = os.path.join(settings.MEDIA_ROOT, seqfile.__str__())                        
            this_seqtype = SeqType.objects.get_or_create(short=this_type)[0]

            # note: taxa_seq[taxon name] = sequence
            (validflag, msg) = is_valid_fasta(fullpath)
            
            if validflag:
                taxa_seq = get_taxa(fullpath, this_format)      
                for taxa in taxa_seq:
                    t = Taxon.objects.get_or_create(name=taxa,
                                                seqtype=this_seqtype,
                                                nsites = taxa_seq[taxa].__len__() )[0]
                    t.save()
                    seqfile.contents.add(t)
                    seqfile.save()    
                
                if ii == 0: 
                    """AA"""
                    this_job.settings.original_aa_file = seqfile
                if ii == 1: 
                    """Codons"""
                    this_job.settings.original_codon_file = seqfile
                    this_job.settings.has_codon_data = True
                this_job.settings.save()
                this_job.save()
                          
            else:
                error_messages.append( msg )
                if ii == 0:
                    this_job.settings.original_aa_file = None
                if ii == 1:
                    this_job.settings.original_codon_file = None
                this_job.settings.save()
                seqfile.delete()
                if ii == 0:
                    aa_seqfileform.fields['aaseq_path'].errors = "Please select a FASTA-formatted file of amino acid sequences."
                    #error_messages.append("Please select a FASTA-formatted file of amino acid sequences.")
                if ii == 1:
                    codon_seqfileform.fields['codonseq_path'].errors = "Please select a FASTA-formatted file of codon sequences."
                    #error_messages.append("Please select a FASTA-formatted file of codon sequences.")
                this_job.settings.save()
                this_job.save()
                 
             
             
        """
            Now update the JobSettings object
        """
        if 'name' in request.POST:
            this_job.settings.name = request.POST.get('name')
        if 'project_description' in request.POST:
            this_job.settings.project_description = request.POST.get('project_description')
       
        selected_msa_algs = request.POST.getlist('alignment_algorithms')
        this_job.settings.alignment_algorithms.clear()
        for mid in selected_msa_algs:
            this_alg = AlignmentAlgorithm.objects.get(id = mid)
            this_job.settings.alignment_algorithms.add( this_alg )
        
        selected_raxml_models = request.POST.getlist('raxml_models')
        this_job.settings.raxml_models.clear()
        for rid in selected_raxml_models:
            this_model = RaxmlModel.objects.get(id = rid)
            this_job.settings.raxml_models.add( this_model )
        
        this_job.settings.start_motif = request.POST.get('start_motif')
        this_job.settings.end_motif = request.POST.get('end_motif')
        this_job.settings.n_bayes_samples = request.POST.get('n_bayes_samples')
        this_job.settings.save()        
        this_job.save()
    
        if this_job.settings.original_aa_file and this_job.settings.name:
            return HttpResponseRedirect('/portal/compose2')

    if False == first_time_composing:
        if this_job.settings.name == None or this_job.settings.name == "":
            error_messages.append("Please choose a name for this job.")

    """
        Finally render the page
    """

    if this_job.settings.original_aa_file and this_job.settings.name:
        forward_unlock = True
    else:
        forward_unlock = False
        

    aa_seqfileform = AASeqFileForm()
    selected_aaseqfile = None
    selected_aaseqfile_short = None
    if this_job.settings.original_aa_file:
        aa_seqfileform.fields["aaseq_path"].default = this_job.settings.original_aa_file.aaseq_path
        selected_aaseqfile =  settings.STATIC_MEDIA_URL + this_job.settings.original_aa_file.aaseq_path.__str__()
        selected_aaseqfile_short = selected_aaseqfile.split("/")[ selected_aaseqfile.split("/").__len__()-1 ]
    
    codon_seqfileform = CodonSeqFileForm()
    selected_codonseqfile = None
    selected_codonseqfile_short = None
    if this_job.settings.original_codon_file:
        codon_seqfileform.fields["codonseq_path"].default = this_job.settings.original_codon_file.codonseq_path
        selected_codonseqfile = settings.STATIC_MEDIA_URL +  this_job.settings.original_codon_file.codonseq_path.__str__()
        selected_codonseqfile_short = selected_codonseqfile.split("/")[ selected_codonseqfile.split("/").__len__()-1 ]
        
    constrainttree_fileform = ConstraintTreeFileForm()
    selected_constrainttreefile = None
    selected_constrainttreefile_short = None
    if this_job.settings.constraint_tree_file:
        constrainttree_fileform.fields["constrainttree_path"].default = this_job.settings.constraint_tree_file.constrainttree_path
        selected_constrainttreefile = settings.STATIC_MEDIA_URL +  this_job.settings.constraint_tree_file.constrainttree_path.__str__()
        selected_constrainttreefile_short = selected_constrainttreefile.split("/")[ selected_constrainttreefile.split("/").__len__()-1 ]
        
    js_form = JobSettingForm()
    js_form.fields["name"].initial = this_job.settings.name
    js_form.fields["project_description"].initial = this_job.settings.project_description
    if this_job.settings.name == None: # first time editing the job
        js_form.fields["alignment_algorithms"].initial = AlignmentAlgorithm.objects.all()
        js_form.fields["raxml_models"].initial = RaxmlModel.objects.all()
    else:
        if this_job.settings.alignment_algorithms:
            js_form.fields["alignment_algorithms"].initial = this_job.settings.alignment_algorithms.all()
        if this_job.settings.raxml_models:
            js_form.fields["raxml_models"].initial = this_job.settings.raxml_models.all()
    js_form.fields["start_motif"].initial = this_job.settings.start_motif
    js_form.fields["end_motif"].initial = this_job.settings.end_motif
    js_form.fields["n_bayes_samples"].initial = this_job.settings.n_bayes_samples

    context_dict = {'aa_seqfileform':       aa_seqfileform,
                    'aa_seqfile_url':       selected_aaseqfile,
                    'aa_seqfile_short':     selected_aaseqfile_short,
                    'codon_seqfileform':    codon_seqfileform,
                    'codon_seqfile_url':    selected_codonseqfile,
                    'codon_seqfile_short':  selected_codonseqfile_short,
                    'constrainttree_seqfileform':    constrainttree_fileform,
                    'constrainttree_seqfile_url':    selected_constrainttreefile,
                    'constrainttree_seqfile_short':  selected_constrainttreefile_short,
                    'error_messages':       error_messages,
                    'js_form':js_form,
                    'forward_unlock':forward_unlock,
                    'current_step':1}
    return render(request, 'portal/compose1.html', context_dict)

@login_required
def compose2(request):        
    this_job = get_mr_job(request)
    context = RequestContext(request)

    outgroup_name = "outgroup"
    matching_groups = this_job.settings.taxa_groups.filter(name=outgroup_name)
    if not matching_groups:
        """If this job is lacking an outgroup, then create it."""
        newgroup = TaxaGroup.objects.create(name=outgroup_name, owner=request.user)
        newgroup.save()
        this_job.settings.taxa_groups.add( newgroup )
        this_job.settings.save()

    if request.method == 'POST':
        if request.POST['action'] == 'setoutgroup':
            checked_taxa = request.POST.getlist('taxa')
            
            print "236:", checked_taxa
            
            """Remove any previously-saved taxa in the outgroup"""
            outgroup = this_job.settings.taxa_groups.filter(name=outgroup_name)[0] 
            outgroup.clear_all()
            outgroup.save()
            
            """Save the currently-checked taxa into the outgroup"""
            for taxa in this_job.settings.original_aa_file.contents.filter(id__in=checked_taxa): # for each checked taxon
                outgroup.taxa.add(taxa)
                print "246:", taxa
            outgroup.save()

            """Save the outgroup to the Job Setting"""
            this_job.settings.outgroup = outgroup
            this_job.settings.save()
            this_job.save()

            if this_job.validate():
                """enqueue_job launches the job!"""
                enqueue_job(request, this_job)
                return HttpResponseRedirect('/portal/status/' + this_job.id.__str__())
            else:
                return HttpResponseRedirect('/portal/compose2')
   
    outgroup_ids = []
    for taxon in this_job.settings.taxa_groups.filter(name=outgroup_name)[0].taxa.all():
        outgroup_ids.append( taxon.id )
        print "264:", taxon.id
        
    taxon_tuples = []
    for taxon in this_job.settings.original_aa_file.contents.all():
        checked = False
        if taxon.id in outgroup_ids:
            checked = True
            print "271:", taxon.id
        nsites = 0
        this_job
        taxon_tuples.append( (taxon.name, taxon.id, checked, taxon.nsites) )
        

    #outgroup_taxon_form = TaxaGroupForm()
    #outgroup_taxon_form.fields["taxa"].queryset = this_job.settings.original_aa_file.contents.all()
    
    #list_of_ancestors = []
    #for aa in this_job.settings.ancestors.all():
    #    list_of_ancestors.append( aa.ancname )
    
    #newanc_form = AncestorForm()
    #newanc_form.fields['ingroup'].queryset = this_job.settings.taxa_groups
    #newanc_form.fields['seedtaxa'].queryset = this_job.settings.original_aa_file.contents.all()
    
    #anccomp_form = AncCompForm()
    #anccomp_form.fields["oldanc"].queryset = this_job.settings.ancestors.all()
    #anccomp_form.fields["newanc"].queryset = this_job.settings.ancestors.all()
    
    #outgroup_form = OutgroupForm()
    #outgroup_form.fields['outgroup'].queryset = this_job.settings.taxa_groups
    #if this_job.settings.outgroup:
    #    outgroup_form.fields['outgroup'].initial = this_job.settings.outgroup
     
    #list_of_anccomps = []
    #for ac in this_job.settings.anc_comparisons.all():
    #    list_of_anccomps.append( (ac.oldanc.ancname, ac.oldanc.id, ac.newanc.ancname, ac.newanc.id) )

    context_dict = {'forward_unlock': True,
                    'jobname': this_job.settings.name,
                    #'outgroup_form':outgroup_taxon_form,
                    'taxon_tuples': taxon_tuples,
                    #'list_of_taxagroups':list_of_taxagroups,
                    #'outgroup_form':outgroup_form,
                    #'outgroup':this_job.settings.outgroup,
                    #'list_of_ancestors': list_of_ancestors,
                    #'newanc_form':newanc_form,
                    #'list_of_anccomps':list_of_anccomps,
                    #'anccomp_form':anccomp_form,
                    'current_step':2}

    return render(request, 'portal/compose2.html', context_dict)
    

@login_required
def jobstatus(request, jobid):
    job = None
    if jobid:
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
        action = request.POST.get('action')
        if action == "edit":
            this_jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=this_jobid)            
            return HttpResponseRedirect('/portal/compose/' + this_jobid)
        if action == "remove":
            this_jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=this_jobid)[0]
            trash_job(request, this_job)            
        if action == "reset":
            this_jobid = request.POST.get( 'jobid' )
            this_job = Job.objects.filter(owner=request.user, id=this_jobid)[0]
            reset_job( request, this_job ) 
        if action == "stop":
            this_jobid = request.POST.get( 'jobid' )
            this_job = Job.objects.filter(owner=request.user, id=this_jobid)[0]
            dequeue_job( request, this_job ) 
        if action == "start":
            this_jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=this_jobid)[0]
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
    
    
    selected_aaseqfile = None
    selected_aaseqfile_short = None
    if job.settings.original_aa_file:
        selected_aaseqfile =  settings.STATIC_MEDIA_URL + job.settings.original_aa_file.aaseq_path.__str__()
        selected_aaseqfile_short = selected_aaseqfile.split("/")[ selected_aaseqfile.split("/").__len__()-1 ]
    
        
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
    
    job.p_done = 100.0 * float(checkpoint)/9.0
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
    
    if checkpoint > 8:
        alib = phylobotmodels.AncestralLibrary.objects.get_or_create(shortname=job.settings.name)[0]
        finished_library_id = alib.id.__str__()
        print "409:", finished_library_id
        #
        #  continue here - get finished_library_id into the template
        #
    
    context_dict = {'job': job, 
                    'job_status': job_status,
                    'nseqs':job.settings.original_aa_file.contents.count(),
                    'list_of_aa':list_of_aa,
                    'list_of_rm':list_of_rm,
                    'checkpoints':checkpoints,
                    'current_checkpoint':checkpoint,
                    'finished_library_id':finished_library_id,
                    'selected_aaseqfile_short':selected_aaseqfile_short,
                    'selected_aa_seqfile_url':selected_aaseqfile,
                    }
    
    return render(request, 'portal/status.html', context_dict)


@login_required
def cancelcompose(request):
    """Cancel a job composition. . . basically delete a bunch of database objects
    that were created, but which are now unecessary."""
    this_job = get_mr_job(request)
    if this_job.settings.name == None:
        trash_job(request, this_job)
    return HttpResponseRedirect('/portal/')