import os

from dendropy import Tree

from django import forms
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.template import RequestContext, Context, loader

from phylobot.models import *
from phylobot.phyloxml_helper import *

import sqlite3 as sqlite
from dendropy import Tree
import math, random

from views_tools import *

import logging
logger = logging.getLogger(__name__)

def view_library(request, libid):
    
    """If a completed ancestral library exists whose name or ID is libid, then
        this method will lead to a view into that library."""
    if libid == None:
        print ". no libid was provided."

    libid = libid.split("/")[0]
    
    """Does libid exist in our known libraries?"""
    foundit = False
    for anclib in AncestralLibrary.objects.all():
        if anclib.id.__str__() == libid or anclib.shortname == libid:
            foundit = True
            libid = anclib.id.__str__()
    if foundit == False:
        logger.error("I cannot find any ancestral libraries with names or IDs that match " + libid.__str__())
        return HttpResponseRedirect('/')
    
    """Retrieve the AncestralLibrary object?"""
    alib = AncestralLibrary.objects.get( id=int(libid) )
    
    """Can we open a connection to this project's SQL database?"""
    con = get_library_sql_connection(libid)
    if con == None:
        logger.error("I cannot open a SQL connection to the database for ancestral library ID " + libid.__str__() )
    
    """
        
        URL Dispatch:
    
    """
    if request.path_info.endswith("alignments"):
        return view_alignments(request, alib, con)
    
    elif request.path_info.endswith(anclib.shortname + ".fasta"):
        """original fasta"""
        tokens = request.path_info.split(".")
        datatype = tokens[   tokens.__len__()-1  ]
        return view_sequences(request, alib, con, format="fasta", datatype=datatype, alignment_method=None)
    
    elif request.path_info.endswith(".fasta"):
        """aligned fasta"""
        tokens = request.path_info.split(".")
        datatype = tokens[   tokens.__len__()-1  ]
        alignment_method = tokens[   tokens.__len__()-2  ]
        #print "62:", tokens
        return view_sequences(request, alib, con, format="fasta", datatype=datatype, alignment_method=alignment_method)
    
    elif request.path_info.endswith(anclib.shortname + ".phylip"):
        """original phylip"""
        tokens = request.path_info.split(".")
        datatype = tokens[   tokens.__len__()-1  ]
        return view_sequences(request, alib, con, format="phylip", datatype=datatype, alignment_method=None)    
    
    elif request.path_info.endswith(".phylip"):
        """aligned phylip"""
        tokens = request.path_info.split(".")
        datatype = tokens[   tokens.__len__()-1  ]
        alignment_method = tokens[   tokens.__len__()-2  ]
        return view_sequences(request, alib, con, format="phylip", datatype=datatype, alignment_method=alignment_method)
       
    elif request.path_info.endswith(".newick"):
        return view_tree(request, alib, con, format="newick")
        
        
    elif request.path_info.endswith("trees"):
        return view_library_trees(request, alib, con)
    
    elif request.path_info.endswith("ancestors"):
        return view_library_ancestortree(request, alib, con)
    
    elif request.path_info.endswith("ml"):
        return view_ancestor_ml(request, alib, con)
    elif request.path_info.endswith("support"):
        return view_ancestor_support(request, alib, con)
    
    elif request.path_info.endswith("supportbysite"):
        return view_ancestor_supportbysite(request, alib, con)
    
    elif request.path_info.endswith("supportbysite.xls"):
        return view_ancestor_supportbysitexls(request, alib, con)
    
    elif request.path_info.__contains__("node"):
        return view_ancestor_ml(request, alib, con)
    
    elif request.path_info.__contains__("mutations"):    
        return view_mutations_bybranch(request, alib, con)
        
    elif request.path_info.endswith("floci"):
        pass
    
    else:
        return view_library_frontpage(request, alib, con)
    
    
    # a hack, for now, to just return the user to the main front page.
    
def get_library_sql_connection(alid):
    """Returns a SQL connection to the database for the AncestralLibrary with id = alid
        If something wrong happens, then this method returns None"""
    if False == AncestralLibrary.objects.filter( id=int(alid) ).exists():
        logger.error("I cannot find an AncestralLibrary object with the id=" + alid.__str__())
        return None
    
    """Open the SQLite3 database:"""
    alib = AncestralLibrary.objects.get( id=int(alid) )
    dbpath = alib.dbpath.__str__()
    dbpath = settings.MEDIA_ROOT + "/" + dbpath
    if False == os.path.exists(dbpath):
        logger.error("I cannot find the AncestralLibrary SQL database at " + dbpath)
        return None
    con = sqlite.connect( dbpath )  
    return con

def get_base_context(request, alib, con):
    """Returns a hashtable with basic facts about the library, including:
        - alid
        - shortname
        - library_name
        - contact_authors
    """
    cur = con.cursor()

    """Fill the context with stuff that's needed for the HTML template."""
    context = {}
    context["alid"] = alib.id
    context["shortname"] = alib.shortname
    
    sql = "select value from Settings where keyword='project_title'"
    cur.execute(sql)
    context["library_name"] = cur.fetchone()[0]
    
    x = alib.contact_authors_profile.all()
    context["contact_authors"] = x  
    
    return context  

def view_library_frontpage(request, alib, con):    
    cur = con.cursor()
    
    context = get_base_context(request, alib, con)

    sql = "select value from Settings where keyword='family_description'"
    cur.execute(sql)
    x = cur.fetchone()
    if x == None:
        context["description"] = ""
    else:
        context["description"] = x[0]
    
    return render(request, 'libview/libview_frontpage.html', context)

def view_sequences(request, alib, con, format="fasta", datatype="aa", alignment_method=None):
    cur = con.cursor()
    
    taxon_seq = {}
    nsites = None
    datatype = 1
    if datatype == "aa":
        datatype = 1
    elif datatype == "codon":
        datatype = 0
    
    if alignment_method == None:    
        sql = "select taxonid, sequence from OriginalSequences where datatype=" + datatype.__str__()
    else:
        sql = "select id from AlignmentMethods where name='" + alignment_method + "'"
        cur.execute(sql)
        x = cur.fetchone()
        if x == None:
            logger.error("I cannot find the aligned sequences for the method named " + alignment_method)
            #
            # continue here: return error
            #
            return HttpResponseRedirect('/')
        else:
            alignment_methodid = x[0]
            sql = "select taxonid, alsequence from AlignedSequences where datatype=" + datatype.__str__() + " and almethod=" + alignment_methodid.__str__()

    """execute the SQL, either with org. seqs. or aligned seqs."""         
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        taxonid = ii[0]
        sequence = ii[1]
        nsites = sequence.__len__()
        sql = "select fullname from Taxa where id=" + taxonid.__str__()
        cur.execute(sql)
        fullname = cur.fetchone()[0]
        taxon_seq[ fullname ] = sequence
    
    context = get_base_context(request, alib, con)
    context["taxon_seq"] = taxon_seq
    if format == "fasta":
        return render(request, 'libview/libview_fasta.fasta', context)
    else:
        context["nsites"] = nsites
        context["ntaxa"] = taxon_seq.keys().__len__()
        return render(request, 'libview/libview_phylip.phylip', context) 

def view_tree(request, alib, con, format="newick"):
    """Most of this method is concerned with determining what tree was requested,
        and, more importantly, if that tree exists in our database."""
    
    cur = con.cursor()
    
    tokens = request.path_info.split(".")
    qq = tokens[ tokens.__len__()-2 ]
    
    context = {}

    sql = "select modelid from PhyloModels where name='" + qq.__str__() + "'"
    cur.execute(sql)
    phylomodelid = cur.fetchone()
    if phylomodelid != None:
        phylomodelid = phylomodelid[0]
    
        #print "210:", qq, phylomodelid
        
        """unsupported ML tree"""    
        tokens = request.path_info.split(".")
        if tokens.__len__() < 4:
            return view_library_frontpage(request, alib, con)
        
        phylomodelname = tokens[ tokens.__len__()-2 ]
        msamodelname = tokens[ tokens.__len__()-3 ]
                
        sql = "select id from AlignmentMethods where name='" + msamodelname + "'"
        cur.execute(sql)
        msamodelid = cur.fetchone()
        if msamodelid == None:
            return view_library_frontpage(request, alib, con)
        msamodelid = msamodelid[0]
        #print "235:", msamodelname, msamodelid
        
        sql = "select newick from UnsupportedMlPhylogenies where almethod=" + msamodelid.__str__() + " and phylomodelid=" + phylomodelid.__str__()
        cur.execute(sql)
        newick = cur.fetchone()
        if newick == None:
            return view_library_frontpage(request, alib, con)
        newick = newick[0]
        #print "243:", newick 
        
        context["newickstring"] = newick
              
    else:
        if tokens.__len__() < 5:
            return view_library_frontpage(request, alib, con)
        
        supportmethodname = tokens[ tokens.__len__()-2 ]
        phylomodelname = tokens[ tokens.__len__()-3 ]
        msamodelname = tokens[ tokens.__len__()-4 ]

        sql = "select modelid from PhyloModels where name='" + phylomodelname + "'"
        cur.execute(sql)
        phylomodelid = cur.fetchone()
        if phylomodelid == None:
            return view_library_frontpage(request, alib, con)
        phylomodelid = phylomodelid[0]
        
        sql = "select id from AlignmentMethods where name='" + msamodelname + "'"
        cur.execute(sql)
        msamodelid = cur.fetchone()
        if msamodelid == None:
            return view_library_frontpage(request, alib, con)
        msamodelid = msamodelid[0]
        
        sql = "select id from BranchSupportMethods where name='" + supportmethodname + "'"
        cur.execute(sql)
        supportmethodid = cur.fetchone()
        if supportmethodid == None:
            return view_library_frontpage(request, alib, con)
        supportmethodid = supportmethodid[0]
        #print "275:", supportmethodname, supportmethodid
        
        sql = "select id from UnsupportedMlPhylogenies where almethod=" + msamodelid.__str__() + " and phylomodelid=" + phylomodelid.__str__()
        cur.execute(sql)
        treeid = cur.fetchone()
        if treeid == None:
            return view_library_frontpage(request, alib, con)
        treeid = treeid[0]
        
        sql = "select newick from SupportedMlPhylogenies where unsupportedmltreeid=" + treeid.__str__() + " and supportmethodid=" + supportmethodid.__str__() 
        cur.execute(sql)
        newick = cur.fetchone()
        if newick == None:
            return view_library_frontpage(request, alib, con)
        newick = newick[0]
        
        context["newickstring"] = newick 
        
    return render(request, 'libview/libview_newick.newick', context)

def view_alignments(request, alib, con):
    cur = con.cursor()
    context = get_base_context(request, alib, con)
    
    """Get a list of alignment methods that were used"""
    sql = "select id, name from AlignmentMethods"
    cur.execute(sql)
    x = cur.fetchall()
    msaids = []
    msaid_names = {}
    for ii in x:
        msaids.append(ii[0])
        msaid_names[  ii[0] ] = ii[1]
    
    """Get sizes of the alignments."""
    msaid_ntaxa = {}
    msaid_nsites = {}
    for msaid in msaid_names:
        sql = "select count(*) from AlignedSequences where almethod=" + msaid.__str__()
        cur.execute(sql)
        count = cur.fetchone()
        #print "205:", count
        count = count[0]
        #print "207:", count
        msaid_ntaxa[msaid] = count 
        sql = "select length(alsequence) from AlignedSequences where almethod=" + msaid.__str__()
        cur.execute(sql)
        length = cur.fetchone()
        length = length[0]
        msaid_nsites[msaid] = length 
        
    msa_tuples = []
    for msaid in msaids:
        refurl = ""
        if msaid_names[msaid] == "msaprobs":
            refurl = "http://bioinformatics.oxfordjournals.org/content/26/16/1958.abstract"
        elif msaid_names[msaid] == "muscle":
            refurl = "http://nar.oxfordjournals.org/content/32/5/1792.full.pdf+html"
        elif msaid_names[msaid] == "prank":
            refurl = "http://www.ebi.ac.uk/goldman-srv/prank/prank/"
        elif msaid_names[msaid] == "mafft":
            refurl = "http://mafft.cbrc.jp/alignment/software/" 
        t = (msaid_names[msaid], msaid_ntaxa[msaid], msaid_nsites[msaid], refurl)
        msa_tuples.append( t )

    context[ "msaid_tuples"] = msa_tuples
    
    return render(request, 'libview/libview_alignments.html', context)

def view_library_trees(request, alib, con):
    cur = con.cursor()
    context = get_base_context(request, alib, con)
    
    """Get a list of trees"""
    sql = "select id, almethod, phylomodelid from UnsupportedMlPhylogenies"
    cur.execute(sql)
    x = cur.fetchall()
    tree_tuples = []
    for ii in x:
        treeid = ii[0]
        almethodid = ii[1]
        phylomodelid = ii[2]
        sql = "select name from AlignmentMethods where id=" + almethodid.__str__()
        cur.execute(sql)
        almethodname = cur.fetchone()[0]
        
        sql = "select name from PhyloModels where modelid=" + phylomodelid.__str__()
        cur.execute(sql)
        phylomodelname = cur.fetchone()[0]
        
        sql = "select likelihood from TreeMl where mltreeid=" + treeid.__str__()
        cur.execute(sql)
        likelihood = cur.fetchone()[0]
        
        sql = "select alpha from TreeAlpha where mltreeid=" + treeid.__str__()
        cur.execute(sql)
        alpha = cur.fetchone()
        if alpha == None:
            alpha = "n/a"
        else:
            alpha = alpha[0]
        
        """Get sum of branch lengths"""
        sql = "select newick from UnsupportedMlPhylogenies where id=" + treeid.__str__()
        cur.execute(sql)
        newick = cur.fetchone()[0]
        t = Tree()
        t.read_from_string(newick, "newick")
        sumbranches = t.length()
        
        tuple = (almethodname, phylomodelname, likelihood, 0.0, alpha, sumbranches)
        
        tree_tuples.append(tuple)
    context["tree_tuples"] = tree_tuples
    
    """Get a list of branch support methods."""
    sql = "select name from BranchSupportMethods"
    cur.execute(sql)
    x = cur.fetchall()
    support_methods = []
    for ii in x:
        support_methods.append(ii[0])
    context["support_methods"] = support_methods
    context["lastmethod"] = support_methods[ support_methods.__len__()-1 ]
    
    return render(request, 'libview/libview_trees.html', context)

def view_library_ancestortree(request, alib, con):
    cur = con.cursor() 
    
    (msaid, msaname, phylomodelid, phylomodelname) = get_msamodel(request, alib, con)

    """Save this viewing preference -- it will load automatically next time
        the user comes to the ancestors page."""
    save_viewing_pref(request, alib, con, "lastviewed_msaid", msaid.__str__())        
    save_viewing_pref(request, alib, con, "lastviewed_modelid", phylomodelid.__str__()) 
           
    context = get_base_context(request, alib, con)  
    context["default_msaname"] = msaname
    context["default_modelname"] = phylomodelname
    
    cladogramstring = ""
    sql = "select newick from AncestralCladogram where unsupportedmltreeid in"
    sql += "(select id from UnsupportedMlPhylogenies where almethod=" + msaid.__str__() + " and phylomodelid=" + phylomodelid.__str__() + ")"
    cur.execute(sql)
    newick = cur.fetchone()[0]
    
    print "446:", newick
    
    """Root the tree"""
    dendrotree = Tree()
    dendrotree.read_from_string(newick, "newick")
    sql = "select shortname from Taxa where id in (select taxonid from GroupsTaxa where groupid in (select id from TaxaGroups where name='outgroup'))"
    cur.execute(sql)
    rrr = cur.fetchall()
    outgroup_labels = []
    for iii in rrr:
        outgroup_labels.append( iii[0].__str__() )
    print "457:", outgroup_labels
    mrca = dendrotree.mrca(taxon_labels=outgroup_labels)
    dendrotree.reroot_at_edge(mrca.edge, update_splits=True)
    newick = dendrotree.as_string("newick")
    
    print "460:", newick

    """This following block is a mess. . . but it solves a problem with the Dendropy library.
        This block will fetch the XML string for use with the javascript-based phylogeny viewer.
        The code here is fundamentally a mess -- I can't figure out the API to get an XML
        string directly from the Phylo class. In the meantime, the messy way is to write
        an XML phylogeny to the /tmp folder, and then read the contents of the file to
        get the XML string."""
    tree = Phylo.read(StringIO(newick), "newick")
    xmltree = tree.as_phyloxml()
    Phylo.write(xmltree, "/tmp/" + alib.id.__str__() + ".clado.xml", 'phyloxml')
    fin = open("/tmp/" + alib.id.__str__() + ".clado.xml", "r")
    xmltreelines = fin.readlines()
    fin.close()    
    urlprefix = msaname + "." + phylomodelname
    xmltreestring = ""
    for l in xmltreelines:
        xmltreestring += annotate_phyloxml(l, urlprefix) + " " 
    xmltreestring = re.sub("\n", " ", xmltreestring)
    context["xmltreestring"] = xmltreestring  
    
    sql = "select count(*) from Taxa"
    cur.execute(sql)
    counttaxa = cur.fetchone()[0]
    context["plotheight"] = counttaxa*16
    
    sql = "select name from AlignmentMethods"
    cur.execute(sql)
    x = cur.fetchall()
    msanames = []
    for ii in x:
        msanames.append( ii[0] )
    context["msanames"] = msanames
    
    context["modelnames"] = get_modelnames(con)
    
    return render(request, 'libview/libview_anctrees.html', context)

def get_ml_sequence(con, ancid):
    cur = con.cursor()
    sql = "select site, state, pp from AncestralStates where ancid=" + ancid.__str__()
    cur.execute(sql)
    x = cur.fetchall()
    
    site_state = {}
    site_mlpp = {}
    
    for ii in x:
        site = ii[0]
        state = ii[1]
        if state == "-":
            continue
        pp = ii[2]
        if site not in site_state:
            site_state[site] = state
            site_mlpp[site] = pp
        if pp > site_mlpp[site]:
            site_state[site] = state
            site_mlpp[site] = pp
    
    sites = site_state.keys()
    sites.sort()
    mlseq = ""
    for s in sites:
        mlseq += site_state[s]
    return mlseq

def get_site_state_pp(con, ancid, skip_indels = True):
    cur = con.cursor()
    sql = "select site, state, pp from AncestralStates where ancid=" + ancid.__str__()
    cur.execute(sql)
    x = cur.fetchall()
    
    site_state_pp = {}
    
    for ii in x:
        site = ii[0]
        state = ii[1]
        if skip_indels and state == "-":
            continue
        pp = ii[2]
        if site not in site_state_pp:
            site_state_pp[site] = {}
        site_state_pp[site][state] = pp
    return site_state_pp

def get_ml_state_pp(state_pp):
    """state_pp is a hashtable, key = state, value = pp of that state
        This method returns the tuple: (ml state, ml pp)"""
    mlstate = None
    mlpp = None
    for state in state_pp:
        pp = state_pp[state]
        if mlstate == None:
            mlstate = state
            mlpp = pp
        elif mlpp < pp:
            mlstate = state
            mlpp = pp
    return (mlstate, mlpp)

def get_anc_stats(con, ancid, n_randoms=5, stride = 0.1, bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]):
    site_state_pp = get_site_state_pp(con, ancid, skip_indels = True)

    """Build a list of alternative Bayesian-sampled ancestral sequences."""
    alt_sequences = []
    for ii in range(0, n_randoms):
        mlseq = ""
        sites = site_state_pp.keys()
        sites.sort()
        for site in sites:
            states = site_state_pp[site].keys()
            random.shuffle(states)
            count = 0.0
            target = random.random()
            for state in states:
                pp = site_state_pp[site][state] 
                if pp == 1.0:
                    mlseq += state
                    break
                elif count >= target:
                    mlseq += state
                    break
                else:
                    count += pp
        alt_sequences.append( mlseq )
        
    """Build a list of PPs for the ML sequence only."""
    mlpps = []
    for site in site_state_pp:
        mlpp = 0.0
        mlstate = None
        for state in site_state_pp[site]:
            pp = site_state_pp[site][state]
            if pp > mlpp:
                mlpp = pp
                mlstate = state
        mlpps.append( mlpp )
        
    """Bin the ML PPs."""
    bin_count = {}    
    for b in bins:
        bin_count[b] = 0.0
    for pp in mlpps:
        for b in bins:
            if pp >= b and pp < b+stride:
                bin_count[b] += 1
                break
    
    nsites = mlpps.__len__()
    bin_freqs = {}
    for b in bins:
        bin_freqs[b] = bin_count[b] / float(nsites)
    
    bin_freq_tuples = []
    for b in bins:
        if b == 1.0:
            bin_freq_tuples.append( (b, b, bin_freqs[b]) )
        else:
            bin_freq_tuples.append( (b, b+stride, bin_freqs[b]) )
        
    mean_pp = get_mean(mlpps)
    sd_pp = get_sd(mlpps)
    
    return (alt_sequences, bin_freq_tuples, mean_pp, sd_pp)

def get_mean(values):
    """Returns the mean, or None if there are 0 values."""
    if values.__len__() == 0:
        return None
    sum = 0.0
    for v in values:
        sum += float(v)
    return sum / float(values.__len__())

def get_sd(values):
    mean = get_mean(values)
    if mean == None:
        return None
    sumofsquares = 0.0
    for v in values:
        sumofsquares += (v - mean)**2
    return math.sqrt( sumofsquares / float(values.__len__()) )

def view_ancestor_ml(request, alib, con):
    cur = con.cursor()
    tokens = request.path_info.split("/")
    setuptoken = tokens[ tokens.__len__()-2 ]
    ttok = setuptoken.split(".")
    if ttok.__len__() != 2:
        return view_library_frontpage(request, alib, con)
    msaname = ttok[0]

    sql = "select id from AlignmentMethods where name='" + msaname.__str__() + "'"
    cur.execute(sql)
    msaid = cur.fetchone()
    if msaid == None:
        return view_library_frontpage(request, alib, con)
    msaid = msaid[0]
  
    phylomodelname = ttok[1]      
    sql = "select modelid from PhyloModels where name='" + phylomodelname.__str__() + "'"
    cur.execute(sql)
    phylomodelid = cur.fetchone()
    if phylomodelid == None:
        return view_library_frontpage(request, alib, con)
    phylomodelid = phylomodelid[0]

    nodetoken = tokens[ tokens.__len__()-1 ].split(".")[0]
    nodenumber = re.sub("node", "", nodetoken)
    sql = "select id from Ancestors where almethod=" + msaid.__str__()
    sql += " and phylomodel=" + phylomodelid.__str__()
    sql += " and name='Node" + nodenumber.__str__() + "'"
    cur.execute(sql)
    x = cur.fetchone()
    if x == None:
        return view_library_frontpage(request, alib, con)
    ancid = x[0]

    seq = get_ml_sequence(con, ancid)
#     ml_sequence = ""
#     for index, char in enumerate(seq):
#         ml_sequence += char
#         if index%70 == 0 and index>1:
#             ml_sequence += "<br>"
    stride = 0.1
    bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    (alt_seqs, bin_freq_tuples, mean_pp, sd_pp) = get_anc_stats(con, ancid, n_randoms=5, stride=stride, bins=bins)

    #print "557:", ancid, msaname, phylomodelname
    context = get_base_context(request, alib, con)
    context["node_number"] = nodenumber
    context["msaname"] = msaname
    context["modelname"] = phylomodelname
    context["ml_sequence"] = seq
    context["alt_sequences"] = alt_seqs
    #context["urlprefix"] = alib.id.__str__() + "/" + msaname + "." + phylomodelname + "/node" + nodenumber.__str__()
    return render(request, 'libview/libview_ancestor_ml.html', context)
        
def view_ancestor_support(request, alib, con):
    cur = con.cursor()
    tokens = request.path_info.split("/")
    setuptoken = tokens[ tokens.__len__()-2 ]
    ttok = setuptoken.split(".")
    if ttok.__len__() != 2:
        return view_library_frontpage(request, alib, con)
    msaname = ttok[0]

    sql = "select id from AlignmentMethods where name='" + msaname.__str__() + "'"
    cur.execute(sql)
    msaid = cur.fetchone()
    if msaid == None:
        return view_library_frontpage(request, alib, con)
    msaid = msaid[0]
  
    phylomodelname = ttok[1]      
    sql = "select modelid from PhyloModels where name='" + phylomodelname.__str__() + "'"
    cur.execute(sql)
    phylomodelid = cur.fetchone()
    if phylomodelid == None:
        return view_library_frontpage(request, alib, con)
    phylomodelid = phylomodelid[0]

    nodetoken = tokens[ tokens.__len__()-1 ].split(".")[0]
    nodenumber = re.sub("node", "", nodetoken)
    sql = "select id from Ancestors where almethod=" + msaid.__str__()
    sql += " and phylomodel=" + phylomodelid.__str__()
    sql += " and name='Node" + nodenumber.__str__() + "'"
    cur.execute(sql)
    x = cur.fetchone()
    if x == None:
        return view_library_frontpage(request, alib, con)
    ancid = x[0]

    seq = get_ml_sequence(con, ancid)
#     ml_sequence = ""
#     for index, char in enumerate(seq):
#         ml_sequence += char
#         if index%70 == 0 and index>1:
#             ml_sequence += "<br>"
    stride = 0.1
    bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    (alt_seqs, bin_freq_tuples, mean_pp, sd_pp) = get_anc_stats(con, ancid, n_randoms=5, stride=stride, bins=bins)


    context = get_base_context(request, alib, con)

    site_state_pp = get_site_state_pp(con, ancid, skip_indels = True)
    sites = site_state_pp.keys()
    sites.sort()
    context["site_support_tuples"] = []
    count_sites = 0
    for site in sites:
        count_sites += 1
        pp_states = {}
        for state in site_state_pp[site]:
            pp = site_state_pp[site][state]
            if pp in pp_states:
                pp_states[pp].append( state)
            else:
                pp_states[pp] = [state]
        pps = pp_states.keys()
        pps.sort(reverse=True)
        states_ordered = []
        pps_ordered = []
        for pp in pps:
            for state in pp_states[pp]:
                states_ordered.append( state )
                pps_ordered.append( pp )
        #print "754:", site, pps_ordered
        mlpp = pps_ordered[0]
        if pps_ordered.__len__() > 1:
            pp2 = pps_ordered[1]
        else:
            pp2 = 0.0
        if pps_ordered.__len__() > 2:
            pp3 = pps_ordered[2]
        else:
            pp3 = 0.0
        context["site_support_tuples"].append(   (count_sites, mlpp, pp2, pp3)  )
    context["last_site"] = sites[ sites.__len__()-1 ]

    #print "557:", ancid, msaname, phylomodelname

    context["node_number"] = nodenumber
    context["msaname"] = msaname
    context["modelname"] = phylomodelname
    context["bin_freq_tuples"] = bin_freq_tuples
    context["stride"] = stride
    context["mean_pp"] = mean_pp
    context["sd_pp"] = sd_pp
    #context["urlprefix"] = alib.id.__str__() + "/" + msaname + "." + phylomodelname + "/node" + nodenumber.__str__()
    return render(request, 'libview/libview_ancestor_support.html', context)      

def view_ancestor_supportbysite(request, alib, con, xls=False):
    cur = con.cursor()
    tokens = request.path_info.split("/")
    setuptoken = tokens[ tokens.__len__()-2 ]
    ttok = setuptoken.split(".")
    if ttok.__len__() != 2:
        return view_library_frontpage(request, alib, con)
    msaname = ttok[0]

    sql = "select id from AlignmentMethods where name='" + msaname.__str__() + "'"
    cur.execute(sql)
    msaid = cur.fetchone()
    if msaid == None:
        return view_library_frontpage(request, alib, con)
    msaid = msaid[0]
  
    phylomodelname = ttok[1]      
    sql = "select modelid from PhyloModels where name='" + phylomodelname.__str__() + "'"
    cur.execute(sql)
    phylomodelid = cur.fetchone()
    if phylomodelid == None:
        return view_library_frontpage(request, alib, con)
    phylomodelid = phylomodelid[0]

    nodetoken = tokens[ tokens.__len__()-1 ].split(".")[0]
    nodenumber = re.sub("node", "", nodetoken)
    sql = "select id from Ancestors where almethod=" + msaid.__str__()
    sql += " and phylomodel=" + phylomodelid.__str__()
    sql += " and name='Node" + nodenumber.__str__() + "'"
    cur.execute(sql)
    x = cur.fetchone()
    if x == None:
        return view_library_frontpage(request, alib, con)
    ancid = x[0]

    site_state_pp = get_site_state_pp(con, ancid, skip_indels = True)
        
    # site_tuples is a list-ified version of site_state_pp, such that
    # the Django template library can deal with it.
    site_rows = []
    
    #site_tuples = {}
    count_sites = 0
    for site in site_state_pp:
        count_sites += 1
        pp_states = {}
        for state in site_state_pp[site]:
            pp = site_state_pp[site][state]
            if pp not in pp_states:
                pp_states[pp] = []
            pp_states[pp].append(state)
        pps = pp_states.keys()
        pps.sort(reverse=True)
        
        tuples = []
        for pp in pps:
            for state in pp_states[pp]:
                tuple = (state, pp)
                tuples.append( tuple )
        site_rows.append( [site,count_sites,tuples] )
    
            
    context = get_base_context(request, alib, con)
    context["node_number"] = nodenumber
    context["msaname"] = msaname
    context["modelname"] = phylomodelname
    #context["urlprefix"] = alib.id.__str__() + "/" + msaname + "." + phylomodelname + "/node" + nodenumber.__str__()
    context["site_rows"] = site_rows
    if xls == True:
        return render(request, 'libview/libview_ancestor_supportbysite.xls', context, content_type='text')
    return render(request, 'libview/libview_ancestor_supportbysite.html', context)   


def view_ancestor_supportbysitexls(request, alib, con):
    return view_ancestor_supportbysite(request, alib, con, xls=True)


def view_mutations_bybranch(request, alib, con):
    cur = con.cursor()
    context = get_base_context(request, alib, con)  

    """Which alignment and model is/was selected?"""
    (msaid, msaname, phylomodelid, phylomodelname) = get_msamodel(request, alib, con)

    """Which ancestors are selected (used to define the branch)"""
    fields = ["ancname1", "ancname2"]
    ancname1 = ""
    ancid1 = None
    ancname2 = ""
    ancid2 = None
    for index, field in enumerate(fields):
        if field in request.POST:
            cur = con.cursor()
            ancname = request.POST.get(field)
            sql = "select name, id from Ancestors where name='" + ancname + "' and almethod=" + msaid.__str__() + " and phylomodel=" + phylomodelid.__str__()
            cur.execute(sql)
            x = cur.fetchone()
            if x != None:
                ancid = x[1]
                if index == 0:
                    ancname1 = ancname
                    ancid1 = ancid
                elif index == 1:
                    ancname2 = ancname
                    ancid2 = ancid
    
    """Deal with missing data in the HTML form by just grabbing the first ancestor from the database"""
    if ancid1 == None:
        sql = "select name, id from Ancestors where almethod=" + msaid.__str__() + " and phylomodel=" + phylomodelid.__str__()
        cur.execute(sql)
        x = cur.fetchone()
        ancid1 = x[1]
        ancname1 = x[0]
    if ancid2 == None:
        sql = "select name, id from Ancestors where almethod=" + msaid.__str__() + " and phylomodel=" + phylomodelid.__str__()
        cur.execute(sql)
        x = cur.fetchone()
        ancid2 = x[1]
        ancname2 = x[0]

    print "917", msaid, msaname, phylomodelid, phylomodelname, ancid1, ancname2, ancid2, ancname2

    """
    Get mutation information between anc1 and anc2
    """
    anc1_site_state_pp = get_site_state_pp(con, ancid1, skip_indels = False) # False is important here, so that the sequence will match the seed sequence in length.
    anc2_site_state_pp = get_site_state_pp(con, ancid2, skip_indels = False)
    seedsequence = get_seed_sequence(con, msaname)
    
    sql = "select value from Settings where keyword='seedtaxa'"
    cur.execute(sql)
    seedtaxonname = cur.fetchone()[0]
    context["seedtaxonname"] = seedtaxonname
    
    #print "929", seedsequence, seedsequence.__len__()
        
    sites = anc1_site_state_pp.keys()
    sites.sort()
    
    #print "931", sites.__len__()
    
    mutation_rows = []
    
    for site in sites:
        (anc1state, anc1pp) = get_ml_state_pp( anc1_site_state_pp[site] )
        (anc2state, anc2pp) = get_ml_state_pp( anc2_site_state_pp[site] )
        if site <= seedsequence.__len__():
            seed_state = seedsequence[site-1]
        else:
            seed_state = "-"
    
        if anc1state == "-" and anc2state == "-":
            continue
        
#         sql = "select * from AncestralStates where ancid=" + ancid1.__str__() + " and site=" + site.__str__()
#         cur.execute(sql)
#         print "953: Site:", site
#         print "954:", cur.fetchall()
#         sql = "select * from AncestralStates where ancid=" + ancid2.__str__() + " and site=" + site.__str__()
#         cur.execute(sql)
#         print "957:", cur.fetchall()
        
        mutation_flag = ""
        """Get the state in the seed sequence."""    
        if anc1state == anc2state:
            """No mutation"""
            pass
        elif anc1state == "-" and anc2state != "-":
            mutation_flag = "insertion"
        elif anc2state == "-" and anc1state != "-":
            mutation_flag = "deletion"
        elif anc1state != anc2state and anc1pp > 0.6 and anc2pp > 0.6:
            mutation_flag = "type 1"

        tuple = (site, seed_state, anc1state, anc1pp, anc2state, anc2pp, mutation_flag)
        mutation_rows.append( tuple )

    context["mutation_rows"] = mutation_rows

    """Save this viewing preference -- it will load automatically next time
        the user comes to the ancestors page."""
    save_viewing_pref(request, alib, con, "lastviewed_msaid", msaid.__str__())        
    save_viewing_pref(request, alib, con, "lastviewed_modelid", phylomodelid.__str__()) 

    sql = "select name, id from Ancestors where almethod=" + msaid.__str__() + " and phylomodel=" + phylomodelid.__str__()
    cur.execute(sql)
    x = cur.fetchall()
    context["ancnames"] = []
    for ii in x:
        context["ancnames"].append( ii[0] )
    
    context["msanames"] = get_alignmentnames(con)
    context["modelnames"] = get_modelnames(con)
    
    context["default_msaname"] = msaname
    context["default_modelname"] = phylomodelname
    
    context["default_ancname1"] = ancname1
    context["default_ancname2"] = ancname2

    return render(request, 'libview/libview_mutations_branch.html', context)

