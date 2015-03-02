from portal.view_tools import *
from portal.view_queue import *

@login_required
def composenew(request):
    """Creates a new Job object, then redirects to compose1"""
    newjob = Job.objects.create(owner=request.user)
    newjob.save()
    log( "views.py 55: Created a new job " + newjob.id.__str__() )
    return HttpResponseRedirect('/portal/compose1')


@login_required
def edit_job(request, jobid):
    print "views.py 14 - edit_job"
    print "views.py 15 - ", jobid
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
        print "45: found a POST"
              
        aa_seqfileform = AASeqFileForm(request.POST, request.FILES)
        codon_seqfileform = CodonSeqFileForm(request.POST, request.FILES)
        js_form = JobSettingForm(request.POST)
      
        print "48:", request.FILES
      
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
                print "70:", seqfile.__str__()
                print "71:", filepath

            # full path to the uploaded sequence file.
            fullpath = os.path.join(settings.MEDIA_ROOT, seqfile.__str__())
                        
            this_seqtype = SeqType.objects.get_or_create(short=this_type)[0]
            print "92:", this_seqtype

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
                this_job.settings.save()
                log((request.user).__str__() + " uploaded the file " + seqfile.__str__() + " with " + (len(taxa_seq)).__str__() + " sequences." )
                            
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
            print "348:", mid, this_alg
        
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
        print "Saving the job!"
    
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
    new_taxagroup_form = []
    anccomp_form = []
    list_of_anccomps = []
    newanc_form = []
    outgroup_form = []
    
    this_job = get_mr_job(request)
    
    context = RequestContext(request)
    
    if request.method == 'POST':
        
        #
        # This page has multiple submit forms.
        # Here, we determine which action to take based on
        # which 'submit' button was clicked.
        #        
        
        #
        # Add new taxa group
        #
        if request.POST['action'] == 'creategroup':
            print "Creating a group"
            checked_taxa = request.POST.getlist('taxa')
            new_group_name = request.POST.get('name')
            matching_groups = this_job.settings.taxa_groups.filter(name=new_group_name)
            if not matching_groups:
                newgroup = TaxaGroup.objects.create(name=new_group_name, owner=request.user)
                for taxa in this_job.settings.original_aa_file.contents.filter(id__in=checked_taxa): # for each checked taxon
                    newgroup.taxa.add(taxa)
                newgroup.save()
                this_job.settings.taxa_groups.add( newgroup )
                this_job.settings.save()

        #
        # Delete a taxagroup
        #
        if request.POST['action'] == 'deletegroup':
            name_of_taxagroup = request.POST.get('taxagroup')
            print "189:", name_of_taxagroup
            this_tg = this_job.settings.taxa_groups.get(name=name_of_taxagroup)
            print "Deleting the TaxaGroup", name_of_taxagroup
            if this_job.settings.outgroup == this_tg:
                this_job.settings.outgroup = None
                this_job.settings.save()
            if this_job.settings.taxa_groups.filter(id=this_tg.id).exists():
                this_job.settings.taxa_groups.remove( this_tg )
                this_job.settings.save()
            if this_tg:
                this_tg.delete()
            #print this_taxagroup

        #
        # Set the outgroup
        #
        if request.POST['action'] == 'setoutgroup':
            selected_taxagroup = request.POST.get('outgroup')
            query_results = this_job.settings.taxa_groups.filter(id__in=selected_taxagroup)
            if query_results:
                desired_outgroup = query_results[0]
            else:
                desired_outgroup = None
                                                                                
            print "views.py 200:", desired_outgroup
            this_job.settings.outgroup = desired_outgroup
            this_job.settings.save()

        #
        # Create an ancestor
        #
        if request.POST['action'] == 'addanc':
            new_anc_name = request.POST.get('ancname')
            
            selected_seed_taxon = request.POST.get('seedtaxa')
            print "233:", selected_seed_taxon
            query_results = this_job.settings.original_aa_file.contents.filter(id=selected_seed_taxon)
            if query_results:
                this_seed = query_results[0]
            else:
                this_seed = None
            
            selected_ingroup = request.POST.get('ingroup')
            query_results = this_job.settings.taxa_groups.filter(id__in=selected_ingroup)
            if query_results:
                this_ingroup = query_results[0]
            else:
                this_ingroup = None
            
            print "views_compose.py 226!"
            print this_seed # continue here - this is None, for some reason?
            print this_ingroup
            if this_seed != None and this_ingroup != None:
                newanc = Ancestor.objects.get_or_create(id__in=this_job.settings.ancestors.all(),
                                                    ancname=new_anc_name,
                                                    seedtaxa = this_seed,
                                                    ingroup=this_ingroup,
                                                    outgroup=this_job.settings.outgroup)[0]
                newanc.save()
                log((request.user).__str__() + " added an ancestor named " + new_anc_name)
       
                this_job.settings.ancestors.add( newanc )
                this_job.settings.save()
        
        #
        # Remove an ancestor
        #
        if request.POST['action'] == 'deleteancestor':
            name_of_ancestor = request.POST.get('ancname')
            print "238:", name_of_ancestor
            this_a = this_job.settings.ancestors.get(ancname=name_of_ancestor)
            print "Deleting the Ancestor", name_of_ancestor
            if this_job.settings.ancestors.filter(id=this_a.id).exists():
                this_job.settings.ancestors.remove( this_a )
                this_job.settings.save()
            if this_a:
                this_a.delete()
        
        #
        # Add an ancestral comparison
        #
        if request.POST['action'] == 'addcomp':
            old_anc_id = request.POST.get('oldanc')
            new_anc_id = request.POST.get('newanc')
            print "283:", old_anc_id, new_anc_id
            
            this_oldanc = this_job.settings.ancestors.get(id__in=old_anc_id)
            this_newanc = this_job.settings.ancestors.get(id__in=new_anc_id)
           
            if this_oldanc and this_newanc:
                print "286:", this_oldanc, this_newanc
                newcomp = AncComp.objects.get_or_create(oldanc=this_oldanc, newanc=this_newanc)[0]
                newcomp.save()
                this_job.settings.anc_comparisons.add( newcomp )
                this_job.settings.save()

            
        #
        # Remove an ancestral comparison
        #
        if request.POST['action'] == 'deletecomp':
            old_anc_id = request.POST.get('oldancid')
            this_olda = this_job.settings.ancestors.get(id__in=old_anc_id)
            new_anc_id = request.POST.get('newancid')
            this_newa = this_job.settings.ancestors.get(id__in=new_anc_id)
            if this_olda and this_newa:
                this_comp = this_job.settings.anc_comparisons.filter(oldanc=this_olda, newanc=this_newa)
                if this_comp:
                    this_job.settings.anc_comparisons.remove( this_comp )
                    
                    print "Deleting the ancestral comparison", id_of_oldanc, id_of_newanc
                    this_comp.delete()
        
        if request.POST['action'] == 'done':
            #
            # Launch the job!
            #
            if this_job.validate():
                """enqueue_job launches the job!"""
                enqueue_job(request, this_job)
                return HttpResponseRedirect('/portal/status/' + this_job.id.__str__())
            else:
                return HttpResponseRedirect('/portal/compose2')
    
    """
    Do the following stuff, regardless if it was a post or not.
    """

    list_of_taxagroups = []
    for tg in this_job.settings.taxa_groups.all():
        list_of_taxagroups.append( (tg.name, tg.taxa.all().__len__()) )

    new_taxagroup_form = TaxaGroupForm()
    new_taxagroup_form.fields["taxa"].queryset = this_job.settings.original_aa_file.contents.all()
    
    list_of_ancestors = []
    for aa in this_job.settings.ancestors.all():
        list_of_ancestors.append( aa.ancname )
    
    newanc_form = AncestorForm()
    newanc_form.fields['ingroup'].queryset = this_job.settings.taxa_groups
    newanc_form.fields['seedtaxa'].queryset = this_job.settings.original_aa_file.contents.all()
    
    anccomp_form = AncCompForm()
    anccomp_form.fields["oldanc"].queryset = this_job.settings.ancestors.all()
    anccomp_form.fields["newanc"].queryset = this_job.settings.ancestors.all()
    
    outgroup_form = OutgroupForm()
    outgroup_form.fields['outgroup'].queryset = this_job.settings.taxa_groups
    if this_job.settings.outgroup:
        outgroup_form.fields['outgroup'].initial = this_job.settings.outgroup
     
    list_of_anccomps = []
    for ac in this_job.settings.anc_comparisons.all():
        list_of_anccomps.append( (ac.oldanc.ancname, ac.oldanc.id, ac.newanc.ancname, ac.newanc.id) )

    context_dict = {'forward_unlock': True,
                    'jobname': this_job.settings.name,
                    'new_taxagroup_form':new_taxagroup_form,
                    'list_of_taxagroups':list_of_taxagroups,
                    'outgroup_form':outgroup_form,
                    'outgroup':this_job.settings.outgroup,
                    'list_of_ancestors': list_of_ancestors,
                    'newanc_form':newanc_form,
                    'list_of_anccomps':list_of_anccomps,
                    'anccomp_form':anccomp_form,
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
                print "I couldn't launch the job:", this_job.name, this_job.id
    
    list_of_aa = []
    for aa in this_job.settings.alignment_algorithms.all():
        list_of_aa.append( aa.name )
    list_of_rm = []
    for rm in this_job.settings.raxml_models.all():
        list_of_rm.append( rm.name )
    
    job_status = get_job_status(jobid)
    
    checkpoints = []
    checkpoints.append( (-1,    "Reading sequences") )
    checkpoints.append( (0,     "Aligning sequences") )
    checkpoints.append( (2,     "Inferring ML phylogenies with RAxML") )
    checkpoints.append( (3,     "Calculating aLRT branch support values with PhyML") )
    checkpoints.append( (4,     "Reconstructing ancestral sequences, using Lazarus") )
    checkpoints.append( (5,     "Rooting tree and extracting ancestors.") )
    checkpoints.append( (5.2,   "Screening for functional loci") )
    checkpoints.append( (6,     "Writing an HTML report") )
    checkpoints.append( (7,     "Final Check") )
    
    context_dict = {'job': this_job, 
                    'job_status': job_status,
                    'nseqs':this_job.settings.original_aa_file.contents.count(),
                    'list_of_aa':list_of_aa,
                    'list_of_rm':list_of_rm,
                    'checkpoints':checkpoints
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