import re
from portal.view_tools import *
from portal.view_queue import *

from django.core.exceptions import ObjectDoesNotExist

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
    print "16:", jobid
    this_job = Job.objects.filter(owner=request.user, id=jobid)
    if this_job:
        this_job = this_job[0]
        this_job.last_modified = datetime.datetime.now()
        this_job.save()
    return HttpResponseRedirect('/portal/compose1')


@login_required
def compose1(request):
    """Step 1 of the job composer.
    The protocol is that BEFORE calling this function, touch a Job object, which
    has the effect of creating a new Job.
    That job object will then be loaded upon calling get_mr_job.
    See below for an example.
    """
    context = RequestContext(request)    
    this_job = get_mr_job(request)
    
    print "39:", this_job
    
    """error_messages is a list of strings, each being an error message. The user cannot proceed to step #2
        unless error_messages is empty.
        If the list is not empty, then the error messages will be displayed on the compose page."""
    error_messages = []
    
    first_time_composing = False
    
    if this_job == None or this_job.settings == None:
        first_time_composing = True
        this_js = JobSetting()
        this_js.save()
        this_job.settings = this_js
        this_job.save()
        
    if request.method == 'POST':                
        aa_seqfileform = AASeqFileForm(request.POST, request.FILES)
        codon_seqfileform = CodonSeqFileForm(request.POST, request.FILES)
        js_form = JobSettingForm(request.POST)
        checked_uniprot = request.POST.getlist('is_uniprot')
      
        """
        INPUT SEQUENCES
        
        Read sequence input (i.e. the FASTA file)
        """
        aaseqfile = None
        codonseqfile = None
        taxa_seq = None
        
        inputnames = ["aaseq_path"] #, "codonseq_path"]
        for ii in range(0, inputnames.__len__()):
            
            inputname = inputnames[ii]
            if inputname not in request.FILES:
                continue
            filepath = request.FILES[inputname]
            
            seqfile = None
            this_type = None

            is_uniprot = False
            if ii == 0: 
                """AA"""
                seqfile = AASeqFile(aaseq_path=filepath)
                this_type = "aa"
                if "aa" in checked_uniprot:
                    is_uniprot = True
            elif ii == 1: 
                """Codons"""
                seqfile = CodonSeqFile(codonseq_path=filepath)
                this_type = "codon"
                if "nt" in checked_uniprot:
                    is_uniprot = True
            seqfile.owner = request.user
            
            this_format = "fasta"
            seqfile.format = SeqFileFormat.objects.get_or_create(name=this_format)[0]
            seqfile.save()

            # full path to the uploaded sequence file.
            fullpath = os.path.join(settings.MEDIA_ROOT, seqfile.__str__())                        
            this_seqtype = SeqType.objects.get_or_create(short=this_type)[0]

            """Is the sequence file a valid FASTA file?"""
            impose_limit = True
            if request.user.username == "admin":
                impose_limit = False
            (validflag, msg) = is_valid_fasta(fullpath, is_uniprot=is_uniprot, impose_limit=impose_limit)
            
            if validflag:
                (taxa_seq, error_msgs) = get_taxa(fullpath, this_format)
                if error_msgs.__len__() > 0:
                    error_messages = error_messages + error_msgs
                
                cleaned_taxa_seq = {} 
                for taxon in taxa_seq:
                    sequence = taxa_seq[taxon]
                    uniprot_data = None # are the sequence name formatted according to NCBI?
                    seqname = taxon # the cleaned sequence name
                    
                    if is_uniprot:
                        x = parse_uniprot_seqname( taxon )
                        if x == None:
                            pass
                            # to-do deal with error condition here!
                        (db, uniqueid, entryname, ogs, gn, pe, sv) = x
                        seqname = gn + "." + uniqueid.__str__() 
                        seqname = clean_fasta_name(seqname)                       
                        """Make or get the Taxon"""
                        t = Taxon.objects.get_or_create(name=seqname,
                                                    seqtype=this_seqtype,
                                                    nsites = taxa_seq[taxon].__len__() )[0]
                        t.save()
                        
                        """Remember the NCBI information"""
                        tncbi = TaxonNCBI.objects.get_or_create(taxon=t,
                                                                uniqueid=uniqueid,
                                                                entryname=entryname,
                                                                organismname=ogs,
                                                                genename=gn)[0]
                        tncbi.save()
                    else:
                        """Make or get the Taxon"""
                        seqname = clean_fasta_name(seqname)
                        t = Taxon.objects.get_or_create(name=seqname,
                                                    seqtype=this_seqtype,
                                                    nsites = taxa_seq[taxon].__len__() )[0]
                        t.save()                    

                    """Have we already seen a sequence with this name?"""
                    if seqname in cleaned_taxa_seq:
                        error_messages.append("After cleaning the sequences and names in your FASTA file, the taxon name " + seqname + " appears twice. Please edit your FASTA file and upload again.")
                    else:
                        """Attach the taxon to the SeqFile"""
                        seqfile.contents.add(t)
                        seqfile.save()
                        cleaned_taxa_seq[seqname] = sequence
                                  
                """Write a cleaned FASTA file that will be used in the actual analysis."""
                write_fasta(cleaned_taxa_seq, fullpath)
                
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
                    aa_seqfileform.fields['aaseq_path'].errors = "Your file does not appear to be FASTA formatted. Please select a FASTA file of amino acid sequences."
                    #error_messages.append("Please select a FASTA-formatted file of amino acid sequences.")
                if ii == 1:
                    codon_seqfileform.fields['codonseq_path'].errors = "Your file does not appear to be FASTA formatted. Please select a FASTA file of codon sequences."
                    #error_messages.append("Please select a FASTA-formatted file of codon sequences.")
                this_job.settings.save()
                this_job.save()
                 
        """
            CONSTRAINT TREE
            Read the constraint tree, if it was provided.
        """ 
        inputname = "constrainttree_path"
        if inputname in request.FILES:
            filepath = request.FILES[inputname]
            
            (retflag, emsg) = is_valid_newick(os.path.join(settings.MEDIA_ROOT, "uploaded_sequences/" + filepath.__str__()), source_sequence_names = None)
            
            if retflag == False:
                this_job.settings.constraint_tree_file = None
                this_job.settings.save()
                this_job.save() 
                error_messages.append("Something is wrong with your constraint tree: " + emsg)
            else:
                """Do the following code if the tree reading was successful."""
                ctfile = ConstraintTreeFile(constrainttree_path=filepath)
                ctfile.owner = request.user
                ctfile.save()
                fullpath = os.path.join(settings.MEDIA_ROOT, ctfile.__str__())  
                this_job.settings.constraint_tree_file = ctfile
                this_job.settings.save()
                this_job.save() 
            
        """
            Now update the JobSettings object
        """
        if 'name' in request.POST:
            this_job.settings.name = request.POST.get('name')
            this_job.settings.name = re.sub("'", "\'", this_job.settings.name)
            

        if 'project_description' in request.POST:
            this_job.settings.project_description = request.POST.get('project_description')
            this_job.settings.project_description = re.sub("'", "\'", this_job.settings.project_description)
        """
            USER-SPEC. ALIGNMENTS
        """
        #print "219: files:", request.FILES
        #print "220:", request.POST
        
        user_msa_baseid = "user_msa"
        for file in request.FILES:
            if file.startswith(user_msa_baseid ):
                this_id = request.POST.get( re.sub("_file", "", file) )
                
                this_alignment_name = request.POST.get( re.sub("_file", "_name", file) )
                
                #count_matches = UserMsa.objects.filter(owner=request.user, alignment_name = this_alignment_name).count()
                count_matches = 0
                if count_matches == 0:
                    """We've never seen this user MSA before, so let's create it and process the file."""
                    this_file = UserMsa(owner=request.user,
                                    alignment_name = this_alignment_name,
                                    attachment = request.FILES[file])
                    print "234: this_file:", this_file
                    this_file.save()
                    print "246: file was saved to:", this_file.attachment.path
                    if ( False == os.path.exists(this_file.attachment.path) ):
                        """The file doesn't exist -- i.e., it didn't save to disk for some reason."""
                        msg = "Error, the file " + this_file.attachmnt.name + " was not saved to disk."
                        error_messages.append( msg )
                    else:
                        """The file saved correctly, so let's process it."""
                        fullpath = this_file.attachment.path
                        (validflag, msg) = is_valid_fasta(fullpath, impose_limit=False, check_is_aligned=True)
                        if validflag == False:
                            this_job.settings.save()
                            this_job.save()
                            error_messages.append( "Your alignment file " +  this_alignment_name + " does not appear to be a FASTA-formatted file.")
                            error_messages.append( msg )
                        elif validflag == True:
                            (usermsa_taxon_seq, error_msgs) = get_taxa(fullpath, "fasta", strip_indels=False)
                            cleaned_fasta_seq = {}
                            for t1 in taxa_seq: # the taxon in the input sequences:
                                if t1 not in usermsa_taxon_seq:
                                    error_messages.append("I cannot find the taxon " + t1 + " in your user-supplied alignment " + user_msa_name)
                                else:
                                    cleaned_seqname = clean_fasta_name(t1)
                                    cleaned_taxa_seq[ cleaned_seqname ] = usermsa_taxon_seq[t1]
                            
                            write_fasta(cleaned_taxa_seq, fullpath)
                            print "268: wrote cleaned user-spec alignment fasta to ", fullpath
                else:
                    """This user MSA already exists in the DB, so just get it."""
                    this_file = UserMsa.objects.get(owner=request.user,
                                    alignment_name = this_alignment_name)
                this_job.settings.user_msas.add( this_file )
                this_job.settings.save()
        """ 
        ALIGNMENT ALGORITHMS
            
        Parse the selected alignment algorithm methods, and (optionally) user-supplied alignments
        """
        this_job.settings.alignment_algorithms.clear()
        selected_msa_algs = request.POST.getlist('alignment_algorithms')
                
        for msaalg in selected_msa_algs:                        
            """
            System-defined alignment
            """
            try:
                this_alg = AlignmentAlgorithm.objects.get(id = msaalg)
            except ObjectDoesNotExist:
                error_messages.append("Something is wrong with your alignment method choice:" + msaalg.__str__() )
            except ValueError:
                error_messages.append("Something is wrong with your alignment method choice:" + msaalg.__str__() )
            this_alg.user_defined = False
            this_job.settings.alignment_algorithms.add( this_alg )
        
        selected_raxml_models = request.POST.getlist('raxml_models')
        this_job.settings.raxml_models.clear()
        for rid in selected_raxml_models:
            this_model = RaxmlModel.objects.get(id = rid)
            this_job.settings.raxml_models.add( this_model )
        
        this_job.settings.save()        
        this_job.save()
            
        if this_job.settings.original_aa_file and this_job.settings.name and error_messages.__len__() == 0:
            return HttpResponseRedirect('/portal/compose2')

    if False == first_time_composing and this_job.settings != None:
        if this_job.settings.name == None or this_job.settings.name == "":
            error_messages.append("Please choose a name for this job.")

    """
        Finally render the page
    """
    if this_job.settings.original_aa_file and this_job.settings.name and error_messages.__len__() == 0:
        forward_unlock = True
    else:
        forward_unlock = False
        
    aa_seqfileform = AASeqFileForm()
    selected_aaseqfile = None
    selected_aaseqfile_short = None
    if this_job.settings.original_aa_file:
        aa_seqfileform.fields["aaseq_path"].default = this_job.settings.original_aa_file.aaseq_path
        selected_aaseqfile =  settings.MEDIA_URL + this_job.settings.original_aa_file.aaseq_path.__str__()
        selected_aaseqfile_short = selected_aaseqfile.split("/")[ selected_aaseqfile.split("/").__len__()-1 ]
    
    codon_seqfileform = CodonSeqFileForm()
    selected_codonseqfile = None
    selected_codonseqfile_short = None
    if this_job.settings.original_codon_file:
        codon_seqfileform.fields["codonseq_path"].default = this_job.settings.original_codon_file.codonseq_path
        selected_codonseqfile = settings.MEDIA_URL +  this_job.settings.original_codon_file.codonseq_path.__str__()
        selected_codonseqfile_short = selected_codonseqfile.split("/")[ selected_codonseqfile.split("/").__len__()-1 ]
        
    constrainttree_fileform = ConstraintTreeFileForm()
    selected_constrainttreefile = None
    selected_constrainttreefile_short = None

    if this_job.settings.constraint_tree_file:
        constrainttree_fileform.fields["constrainttree_path"].default = this_job.settings.constraint_tree_file.constrainttree_path
        selected_constrainttreefile = settings.MEDIA_URL +  this_job.settings.constraint_tree_file.constrainttree_path.__str__()
        selected_constrainttreefile_short = selected_constrainttreefile.split("/")[ selected_constrainttreefile.split("/").__len__()-1 ]

    selected_constrainttreefile = None
    selected_constrainttreefile_short = None
        
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
                    #'user_msas':        user_msas,
                    #'countUserMsas':    user_msas.__len__(),
                    'js_form':js_form,
                    'forward_unlock':forward_unlock,
                    'current_step':1}
    return render(request, 'portal/compose1.html', context_dict)

@login_required
def compose2(request):        
    this_job = get_mr_job(request)
    context = RequestContext(request)
    error_messages = []

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
            count_outgroup = 0
            for taxa in this_job.settings.original_aa_file.contents.filter(id__in=checked_taxa): # for each checked taxon
                outgroup.taxa.add(taxa)
                count_outgroup += 1
            outgroup.save()
                        
            if count_outgroup == 0:
                error_messages.append("Please select at least one outgroup sequence.")
            else:
                """Save the outgroup to the Job Setting"""
                this_job.settings.outgroup = outgroup
                this_job.settings.save()
                this_job.save()

            if error_messages.__len__() == 0 and this_job.validate():
                """enqueue_job launches the job!"""
                enqueue_job(request, this_job)
                return HttpResponseRedirect('/portal/status/' + this_job.id.__str__())
   
    outgroup_ids = []
    for taxon in this_job.settings.taxa_groups.filter(name=outgroup_name)[0].taxa.all():
        outgroup_ids.append( taxon.id )
    
    aapath = os.path.join(settings.MEDIA_ROOT, this_job.settings.original_aa_file.__str__()) 
    (taxa_seq, error_msgs) = get_taxa(aapath, "fasta")
       
    taxon_tuples = []
    for taxon in this_job.settings.original_aa_file.contents.all():
        checked = False
        if taxon.id in outgroup_ids:
            checked = True
        nsites = 0
        seq = taxa_seq[ taxon.name ]
        taxon_tuples.append( (taxon.name, taxon.id, checked, taxon.nsites, seq[0:20]) )
        
    context_dict = {'forward_unlock': True,
                    'jobname': this_job.settings.name,
                    'taxon_tuples': taxon_tuples,
                    'error_messages': error_messages,
                    'current_step':2}

    return render(request, 'portal/compose2.html', context_dict)
    
@login_required
def cancelcompose(request):
    """Cancel a job composition. . . basically delete a bunch of database objects
    that were created, but which are now unecessary."""
    this_job = get_mr_job(request)
    if this_job.settings.name == None:
        trash_job(request, this_job)
    return HttpResponseRedirect('/portal/')