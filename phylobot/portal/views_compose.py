from portal.view_tools import *
from portal.view_queue import *

@login_required
def composenew(request):
    """Creates a new Job object, then redirects to compose1"""
    newjob = Job.objects.create(owner=request.user)
    newjob.save()
    return HttpResponseRedirect('/portal/compose1')


@login_required
def edit_job(request, jobid):
    this_job = Job.objects.filter(owner=request.user, id=jobid)
    if this_job:
        this_job = this_job[0]
        this_job.last_modified = datetime.datetime.now()
        this_job.save()
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
    
    if this_job.settings == None:
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
            if is_valid_fasta(fullpath):
                taxa_seq = get_taxa(fullpath, this_format)      
                for taxa in taxa_seq:
                    t = Taxon.objects.get_or_create(name=taxa,
                                                seqtype=this_seqtype)[0]
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
                if ii == 0:
                    this_job.settings.original_aa_file = None
                if ii == 1:
                    this_job.settings.original_codon_file = None
                this_job.settings.save()
                seqfile.delete()
                if is_aa:
                    aa_seqfileform.fields['aaseq_path'].errors = "Please select a FASTA-formatted file of amino acid sequences."
                if is_codon:
                    codon_seqfileform.fields['codonseq_path'].errors = "Please select a FASTA-formatted file of codon sequences."
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
                    'js_form':js_form,
                    'forward_unlock':forward_unlock,
                    'current_step':1}
    return render(request, 'portal/compose1.html', context_dict)

@login_required
def compose2(request):    
    """
    Here's the pieces needed to build the taxa setup page.
    """
#     new_taxagroup_form = []
#     anccomp_form = []
#     list_of_anccomps = []
#     newanc_form = []
#     outgroup_form = []
    
    
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
            
            """Remove any previously-saved taxa in the outgroup"""
            outgroup = this_job.settings.taxa_groups.filter(name=outgroup_name)[0] 
            outgroup.clear_all()
            outgroup.save()
            
            """Save the currently-checked taxa into the outgroup"""
            for taxa in this_job.settings.original_aa_file.contents.filter(id__in=checked_taxa): # for each checked taxon
                outgroup.taxa.add(taxa)
            outgroup.save()

            """Save the outgroup to the Job Setting"""
            this_job.settings.outgroup = outgroup
            this_job.settings.save()
            this_job.save()

#         #
#         # Delete a taxagroup
#         #
#         if request.POST['action'] == 'deletegroup':
#             name_of_taxagroup = request.POST.get('taxagroup')
#             this_tg = this_job.settings.taxa_groups.get(name=name_of_taxagroup)
#             if this_job.settings.outgroup == this_tg:
#                 this_job.settings.outgroup = None
#                 this_job.settings.save()
#             if this_job.settings.taxa_groups.filter(id=this_tg.id).exists():
#                 this_job.settings.taxa_groups.remove( this_tg )
#                 this_job.settings.save()
#             if this_tg:
#                 this_tg.delete()

        #
        # Set the outgroup
        #
#         if request.POST['action'] == 'setoutgroup':
#             selected_taxagroup = request.POST.get('outgroup')
#             query_results = this_job.settings.taxa_groups.filter(id__in=selected_taxagroup)
#             if query_results:
#                 desired_outgroup = query_results[0]
#             else:
#                 desired_outgroup = None
#                                                                                 
#             this_job.settings.outgroup = desired_outgroup
#             this_job.settings.save()

#         #
#         # Create an ancestor
#         #
#         if request.POST['action'] == 'addanc':
#             new_anc_name = request.POST.get('ancname')
#             
#             selected_seed_taxon = request.POST.get('seedtaxa')
#             query_results = this_job.settings.original_aa_file.contents.filter(id=selected_seed_taxon)
#             if query_results:
#                 this_seed = query_results[0]
#             else:
#                 this_seed = None
#             
#             selected_ingroup = request.POST.get('ingroup')
#             query_results = this_job.settings.taxa_groups.filter(id__in=selected_ingroup)
#             if query_results:
#                 this_ingroup = query_results[0]
#             else:
#                 this_ingroup = None
#             
#             if this_seed != None and this_ingroup != None:
#                 newanc = Ancestor.objects.get_or_create(id__in=this_job.settings.ancestors.all(),
#                                                     ancname=new_anc_name,
#                                                     seedtaxa = this_seed,
#                                                     ingroup=this_ingroup,
#                                                     outgroup=this_job.settings.outgroup)[0]
#                 newanc.save()
#                 this_job.settings.ancestors.add( newanc )
#                 this_job.settings.save()
#         
#         #
#         # Remove an ancestor
#         #
#         if request.POST['action'] == 'deleteancestor':
#             name_of_ancestor = request.POST.get('ancname')
#             this_a = this_job.settings.ancestors.get(ancname=name_of_ancestor)
#             if this_job.settings.ancestors.filter(id=this_a.id).exists():
#                 this_job.settings.ancestors.remove( this_a )
#                 this_job.settings.save()
#             if this_a:
#                 this_a.delete()
#         
#         #
#         # Add an ancestral comparison
#         #
#         if request.POST['action'] == 'addcomp':
#             old_anc_id = request.POST.get('oldanc')
#             new_anc_id = request.POST.get('newanc')
#             
#             this_oldanc = this_job.settings.ancestors.get(id__in=old_anc_id)
#             this_newanc = this_job.settings.ancestors.get(id__in=new_anc_id)
#            
#             if this_oldanc and this_newanc:
#                 newcomp = AncComp.objects.get_or_create(oldanc=this_oldanc, newanc=this_newanc)[0]
#                 newcomp.save()
#                 this_job.settings.anc_comparisons.add( newcomp )
#                 this_job.settings.save()
# 
#             
#         #
#         # Remove an ancestral comparison
#         #
#         if request.POST['action'] == 'deletecomp':
#             old_anc_id = request.POST.get('oldancid')
#             this_olda = this_job.settings.ancestors.get(id__in=old_anc_id)
#             new_anc_id = request.POST.get('newancid')
#             this_newa = this_job.settings.ancestors.get(id__in=new_anc_id)
#             if this_olda and this_newa:
#                 this_comp = this_job.settings.anc_comparisons.filter(oldanc=this_olda, newanc=this_newa)
#                 if this_comp:
#                     this_job.settings.anc_comparisons.remove( this_comp )
#                     this_comp.delete()
        
        
     
        if request.POST['action'] == 'done':
            if this_job.validate():
                """enqueue_job launches the job!"""
                enqueue_job(request, this_job)
                return HttpResponseRedirect('/portal/status/' + this_job.id.__str__())
            else:
                return HttpResponseRedirect('/portal/compose2')
   
    outgroup_ids = []
    for taxon in this_job.settings.taxa_groups.filter(name=outgroup_name)[0].taxa.all():
        outgroup_ids.append( taxon.id )
        
    taxon_tuples = []
    for taxon in this_job.settings.original_aa_file.contents.all():
        checked = False
        if taxon.id in outgroup_ids:
            checked = True
        taxon_tuples.append( (taxon.name, taxon.id, checked) )
        

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
    this_job = None
    if jobid:
        try:
            this_job = Job.objects.get(id=jobid)
        except Job.DoesNotExist:
            pass
    if this_job == None:
        this_job = get_mr_job(request)
    
    context = RequestContext(request)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == "edit":
            jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=jobid)            
            return HttpResponseRedirect('/portal/compose/' + jobid)
        if action == "remove":
            jobid = request.POST.get('jobid')
            this_job = Job.objects.filter(owner=request.user, id=jobid)[0]
            trash_job(request, this_job)            
        if action == "reset":
            jobid = request.POST.get( 'jobid' )
            this_job = Job.objects.filter(owner=request.user, id=jobid)[0]
            reset_job( request, this_job ) 
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
                print >> sys.stderr, "I couldn't validate the job: " + this_job.name + " " + this_job.id.__str__()
        if action == "refresh":
            """Default, the rest of this method will do the status refresh"""
            pass
    
    list_of_aa = []
    for aa in this_job.settings.alignment_algorithms.all():
        list_of_aa.append( aa.name )
    list_of_rm = []
    for rm in this_job.settings.raxml_models.all():
        list_of_rm.append( rm.name )
    
    job_status = get_job_status(jobid)
    checkpoint = int( get_aws_checkpoint(jobid) )
    
    checkpoints = []
    checkpoints.append( (1.1,     "Sequence Alignment") )
    checkpoints.append( (2.7,     "Calculate Alignment Support with ZORRO") )
    checkpoints.append( (3.1,     "ML Phylogeny Inference") )
    checkpoints.append( (5,     "Phylogenetic Support") )
    checkpoints.append( (5.11,     "Ancestral Sequence Reconstruction") )
    checkpoints.append( (6.8,   "Screening for Functional Loci") )
    checkpoints.append( (8,     "Done") )
    
    context_dict = {'job': this_job, 
                    'job_status': job_status,
                    'nseqs':this_job.settings.original_aa_file.contents.count(),
                    'list_of_aa':list_of_aa,
                    'list_of_rm':list_of_rm,
                    'checkpoints':checkpoints,
                    'current_checkpoint':checkpoint
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