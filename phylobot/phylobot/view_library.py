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
import math, random

from views_tools import *

import logging
logger = logging.getLogger(__name__)

def view_library(request, libid):
    """If a completed ancestral library exists whose name or ID is libid, then
        this method will lead to a view into that library."""
    
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
    
    elif request.path_info.endswith("zorro"):
        return view_zorro_profiles(request, alib, con)
    
    elif request.path_info.endswith("alignment"):
        tokens = request.path_info.split("/")
        alignment_method = tokens[   tokens.__len__()-2  ]
        
        """The use may have optionally specified some ancestral sequences to overlay in this alignment view."""
        cur = con.cursor()
        show_ancestral_ids = []
        tk = tokens[ tokens.__len__()-1 ]
        tks = tk.split(".")
        if tks.__len__() > 1:
            for t in range(0, tks.__len__()-1):
                nodenumber = int(tks[t])
                sql = "select id from Ancestors where name='Node" + nodenumber.__str__() + "'"
                cur.execute(sql)
                x = cur.fetchone()
                if x == None:
                    continue
                ancid = int( x[0] )
                show_ancestral_ids.append( ancid )
        return view_single_alignment(request, alib, con, alignment_method, show_these_ancestors=show_ancestral_ids)
    
    elif request.path_info.endswith("supportbysite.xls"):
        return view_ancestor_supportbysitexls(request, alib, con)
    
    elif request.path_info.__contains__("Node"):
        return view_ancestor_ml(request, alib, con)

    elif request.path_info.__contains__("sites"):
        return view_sites(request, alib, con)

    elif request.path_info.__contains__("site"):
        return view_site(request, alib, con)
    
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

def view_single_alignment(request, alib, con, alignment_method, show_these_ancestors=[], show_these_test_scores=[]):
    """alignment_method can be either the ID or the name of the method
        
        show_these_ancestors is a list of ancestral IDs that may, optionally, be shown
        above the alignment.
        
        show_these_test_scores is a list of test IDs, whose scores will be displayed above
        the alignment. The test IDs can correspond to either dN/dS tests, or dF tests.
        
    """
    cur = con.cursor()
    
    """Which alignment method?"""
    if alignment_method == None:
        return view_library_frontpage(request, alib, con)
    alignment_methodid = None
    sql = "select name, id from AlignmentMethods where name='" + alignment_method + "'"
    cur.execute(sql)
    x = cur.fetchone()
    if x != None:
        alignment_methodid = int( x[1] )
    else:
        sql = "select name, id from AlignmentMethods where id=" + alignment_method.__str__()
        cur.execute(sql)
        x = cur.fetchone()
        if x != None:
            alignment_methodid = int( x[1] )
    if alignment_methodid == None:
        """We couldn't find this alignment method in the database."""
        return view_library_frontpage(request, alib, con)

    context = get_base_context(request, alib, con)
    context["firstseq"] = None
    
    """Get a list of taxon IDs, in order"""
    sql = "select fullname from Taxa"
    cur.execute(sql)
    x = cur.fetchall()
    taxanames = []
    for ii in x:
        taxanames.append( ii[0].__str__() )
    
    """Fill a.a. taxon_seq"""
    taxon_aaseq = {}    
    sql = "select taxonid, alsequence from AlignedSequences where datatype=1 and almethod=" + alignment_methodid.__str__()       
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        taxonid = ii[0]
        sequence = ii[1]
        if context["firstseq"] == None:
            context["firstseq"] = sequence
        sql = "select fullname from Taxa where id=" + taxonid.__str__()
        cur.execute(sql)
        fullname = cur.fetchone()[0]
        taxon_aaseq[ fullname ] = sequence  

    aa_tuples = []
    for ancid in show_these_ancestors:
        ancseq = get_ml_sequence(con, ancid, skip_indels=False)
        
        ancname = ""
        sql = "select name from Ancestors where id=" + ancid.__str__()
        cur.execute(sql)
        x = cur.fetchone()
        if x!=None:
            ancname = x[0].__str__()
        
        modelname = ""
        sql = "select name from PhyloModels where modelid in (select phylomodel from Ancestors where id=" + ancid.__str__() + ")"
        cur.execute(sql)
        x = cur.fetchone()
        if x != None:
            modelname = x[0]
        
        aa_tuples.append( ("Ancestor " + ancname + " (" + modelname + ")" , ancseq) )
    for name in taxanames:
        aa_tuples.append( (name, taxon_aaseq[name]) )     
    context["taxon_aaseq"] = aa_tuples


    score_tuples = {}
    for testid in show_these_test_scores:
        sql = "select count(*) from FScore_Tests where id=" + testid.__str__()
        cur.execute(sql)
        x = cur.fetchone()[0]
        if x > 0:
            sql = "select site, df from FScore_Sites where testid=" + testid.__str__() + " order by site ASC"
            cur.execute(sql)
            yy = cur.fetchall()
        else:
            sql = "select count(*) from DNDS_Tests where id=" + testid.__str__()
            cur.execute(sql)
            x = cur.fetchone()[0]
            if x > 0:
                sql = "select site, max(pclass3, pclass4) from DNDS_params where testid=" + testid.__str__() + " order by site ASC"
                cur.execute(sql)
                yy = cur.fetchall()
        score_tuples[testid] = []
        for tuple in yy:
            score_tuples[testid].append( tuple[1] )
            
    """Fill codon taxon_seq (optional)"""
    taxon_codonseq = {}    
    sql = "select taxonid, alsequence from AlignedSequences where datatype=0 and almethod=" + alignment_methodid.__str__()       
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        taxonid = ii[0]
        sequence = ii[1]
        sql = "select fullname from Taxa where id=" + taxonid.__str__()
        cur.execute(sql)
        fullname = cur.fetchone()[0]
        taxon_codonseq[ fullname ] = sequence   
    codon_tuples = []
    for ancid in show_these_ancestors:
        sql = "select name from Ancestors where id=" + ancid.__str__()
        cur.execute(sql)
        x = cur.fetchone()
        if x!=None:
            ancname = x[0].__str__()
            codon_tuples.append( (ancname,None) )
    for name in taxanames:
        if name in taxon_codonseq:
            codon_tuples.append( (name, taxon_codonseq[name]) )   
        else:
            codon_tuples.append( (name, None) )
    context["taxon_codonseq"] = codon_tuples
    context["msaname"] = alignment_method
    context["scorerows"] = score_tuples
    return render(request, 'libview/libview_alignment_viz.html', context)


def view_zorro_profiles(request, alib, con):
    cur = con.cursor()
    context = get_base_context(request, alib, con)
    
    sql = "select id from AlignmentSiteScoringMethods where name='zorro'"
    cur.execute(sql)
    x = cur.fetchone()
    zorromethodid = None
    if x != None:
        zorromethodid = int( x[0] )
    
    context[ "zorro_tuples" ] = [] # a list of lists; each list contains tuples (site,score) for the i-th MSA method.
    sql = "select name, id from AlignmentMethods"
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        almethodid = int( ii[1] )
        
        """Get the ZORRO data for this alignment"""
        if zorromethodid != None:
            site_score_tuples = []
            
            sql = "select site, score from AlignmentSiteScores where almethodid=" + almethodid.__str__()
            sql += " and scoringmethodid=" + zorromethodid.__str__()
            sql += " order by site ASC"
            cur.execute(sql)
            yy = cur.fetchall()
            for jj in yy:
                site = int( jj[0] )
                score = float( jj[1] )
                site_score_tuples.append( (site,score) )
            
            lastsite = site_score_tuples[ site_score_tuples.__len__()-1 ][0] 
            context[ "zorro_tuples" ].append( (ii[0], lastsite, site_score_tuples ) )
    
    return render(request, 'libview/libview_zorro_all.html', context)

def view_library_trees(request, alib, con):
    cur = con.cursor()
    context = get_base_context(request, alib, con)
    
    """Get a list of trees"""
    sql = "select id, almethod, phylomodelid from UnsupportedMlPhylogenies"
    cur.execute(sql)
    x = cur.fetchall()
    treeids = [] # store the treeids in order
    tree_tuples = [] # data for the HTML table
    treeid_dendropytree = {} # cache the Newick strings
    for ii in x:
        treeid = ii[0]
        treeids.append( treeid )
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
        
        sql = "select pp from TreePP where mltreeid=" + treeid.__str__()
        cur.execute(sql)
        pp = cur.fetchone()
        if pp == None:
            pp = "n/a"
        else:
            pp = float(pp[0])
        
        """Get sum of branch lengths"""
        sql = "select newick from UnsupportedMlPhylogenies where id=" + treeid.__str__()
        cur.execute(sql)
        newick = cur.fetchone()[0]
        t = Tree()
        t.read_from_string(newick, "newick")
        sumbranches = t.length()
        
        treeid_dendropytree[treeid] = t
                
        tuple = (almethodname, phylomodelname, likelihood, pp, alpha, sumbranches)
        
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
    
    """Compute the distance matrix between phylogenies from different
        method-model pairs."""
    symmd_matrix = []
    maxdistance = 0
    for ii in treeids:
        treeii = treeid_dendropytree[ii]
        this_row = []
        for jj in treeids:
            treejj = treeid_dendropytree[jj]
            distance = treeii.symmetric_difference(treejj)
            if distance > maxdistance:
                maxdistance = distance
            this_row.append( distance )
        symmd_matrix.append( this_row )
    context["symmd_matrix"] = symmd_matrix
    
    symmd_matrix_colorbins = []
    symmd_matrix_colorbins.append( 0.0 )
    symmd_matrix_colorbins.append( 0.1*maxdistance)
    symmd_matrix_colorbins.append( 0.2*maxdistance)
    symmd_matrix_colorbins.append( 0.3*maxdistance)
    symmd_matrix_colorbins.append( 0.4*maxdistance)
    symmd_matrix_colorbins.append( 0.5*maxdistance)
    context["symmd_matrix_colorbins"] = symmd_matrix_colorbins

    eucd_matrix = []
    maxdistance = 0
    for ii in treeids:
        treeii = treeid_dendropytree[ii]
        this_row = []
        for jj in treeids:
            treejj = treeid_dendropytree[jj]
            distance = treeii.euclidean_distance(treejj)
            if distance > maxdistance:
                maxdistance = distance
            this_row.append( distance )
        eucd_matrix.append( this_row )
    context["eucd_matrix"] = eucd_matrix
    
    eucd_matrix_colorbins = []
    eucd_matrix_colorbins.append( 0.0 )
    eucd_matrix_colorbins.append( 0.1*maxdistance)
    eucd_matrix_colorbins.append( 0.2*maxdistance)
    eucd_matrix_colorbins.append( 0.3*maxdistance)
    eucd_matrix_colorbins.append( 0.4*maxdistance)
    eucd_matrix_colorbins.append( 0.5*maxdistance)
    context["eucd_matrix_colorbins"] = eucd_matrix_colorbins

    return render(request, 'libview/libview_trees.html', context)

def reset_all_biopython_branchlengths(root, length):
    print >> sys.stderr, "435: setting al BLs to 1.0"
    print >> sys.stderr, "436: ", root.branch_length
    root.branch_length = length
    for child in root.clades:
        print >> sys.stderr, "437 found a child: " + child.name.__str__()
        child = reset_all_biopython_branchlengths(child, length)
    return root

def view_library_ancestortree(request, alib, con):
    cur = con.cursor() 
    
    (msaid, msaname, phylomodelid, phylomodelname) = get_msamodel(request, alib, con)

    """Save this viewing preference -- it will load automatically next time
        the user comes to the ancestors page."""
    save_viewing_pref(request, alib.id, con, "lastviewed_msaid", msaid.__str__())        
    save_viewing_pref(request, alib.id, con, "lastviewed_modelid", phylomodelid.__str__()) 
           
    context = get_base_context(request, alib, con)  
    context["default_msaname"] = msaname
    context["default_modelname"] = phylomodelname
    
    """Get the cladogram of ancestors"""
    newick = get_anc_cladogram(con, msaid, phylomodelid)
    #newick = reroot_newick(con, newick)
    print >> sys.stderr, "451: " + newick.__str__()
    
    """This following block is a mess. . . but it solves a problem with the Dendropy library.
        This block will fetch the XML string for use with the javascript-based phylogeny viewer.
        The code here is fundamentally a mess -- I can't figure out the API to get an XML
        string directly from the Phylo class. In the meantime, the messy way is to write
        an XML phylogeny to the /tmp folder, and then read the contents of the file to
        get the XML string."""
    #print >> sys.stderr, "458: " + msaid.__str__() + " " + phylomodelid.__str__()
    handle = StringIO(newick)
    #print >> sys.stderr, "458b"
    tree = Phylo.read(handle, "newick")
    
    """This is a small hack to make new versions of BioPython behave with our javascript
        tree visuazliation."""
    
    tree.root = reset_all_biopython_branchlengths(tree.root, 1.0)
    
    #print >> sys.stderr, "464:" + dir(tree).__str__()
    
    #print >> sys.stderr, "459: " + tree.__str__()   
    
    
    #
    # continue here
    #
    xmltree = tree.as_phyloxml()
    #print >> sys.stderr, "470: XMLtree=" + xmltree.__str__()
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

def get_ml_sequence(con, ancid, skip_indels=True):
    cur = con.cursor()
    sql = "select site, state, pp from AncestralStates where ancid=" + ancid.__str__()
    cur.execute(sql)
    x = cur.fetchall()
    
    site_state = {}
    site_mlpp = {}
    
    for ii in x:
        site = ii[0]
        state = ii[1]
        pp = float(ii[2])
        if state == "-" and skip_indels==True:
            continue
        elif state == "-" and skip_indels==False:
            site_state[site] = "-"
        elif site not in site_state:
            site_state[site] = state
            site_mlpp[site] = pp
        elif pp > site_mlpp[site]:
            site_state[site] = state
            site_mlpp[site] = pp            

    sites = site_state.keys()
    sites.sort()
    mlseq = ""
    for s in sites:
        mlseq += site_state[s]
    return mlseq

def ml_sequence_difference(seq1, seq2):
    """Returns the proportion similarity between two sequences.
        If the sequences have different length, then it returns
        0.0."""
    if seq1.__len__() != seq2.__len__():
        return None
    count_sites = 0
    count_matches = 0
    for ii in xrange(0, seq1.__len__() ):
        # skip sites where both sequences are indels.
        if seq1[ii] == "-" and seq2[ii] == "-":
            continue
        count_sites += 1
        if seq1[ii].__str__().upper() == seq2[ii].__str__().upper():
            count_matches += 1
    return float(count_matches) / float(count_sites)

def get_site_state_pp(con, ancid, skip_indels = True):
    """Returns a hashtable, key = site, value = hash; key = residue state, value = PP of the state
        skip_indels will skip those sites with indels"""
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
        if state not in site_state_pp[site]:
            site_state_pp[site][state] = pp
            
    return site_state_pp

def get_site_ml(con, ancid, skip_indels = True):
    """Returns the hashtable; key = site, value = tuple of (mlstate, mlpp)"""
    cur = con.cursor()
    sql = "select site, state, pp from AncestralStates where ancid=" + ancid.__str__()
    cur.execute(sql)
    x = cur.fetchall()
    site_tuple = {}
    site_mlpp = {}
    for ii in x:
        site = ii[0]
        state = ii[1]
        pp = ii[2]
        if site not in site_mlpp:
            site_mlpp[site] = pp
            site_tuple[site] = (state, pp)
        if pp > site_mlpp[site]:
            site_mlpp[site] = pp
            site_tuple[site] = (state, pp)
    return site_tuple

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

def view_sites(request, alib, con):
    """This is the generic sites view, which dispatches to a specific
        site in a specific alignment"""
    cur = con.cursor()
    
    msaid = None
    msaname = None
    phylomodelid = None
    phylomodelname = None
    #x = get_msamodel_from_url(request, con)
    x = get_msamodel(request, alib, con)
    if x != None:
        (msaid, msaname, phylomodelid, phylomodelname) = x
    
    if msaid == None:
        """There was no alignment method in the URL, nor was there a saved viewing preference
            for the default alignment. . . so just pick a random alignment method from the database."""

        sql = "select id, name from AlignmentMethods"
        cur.execute(sql)
        x = cur.fetchone()
        msaid = x[0]
        msaname = x[1]

    """Is there a specified site on the HTML POST form?"""
    site = None
    if request.method == "POST":
        if "site" in request.POST:
            site = int( request.POST.get("site") )
    if site == None or site < 1:
        x = get_viewing_pref(request, alib.id, con, "lastviewed_site_msa=" + msaid.__str__() )
        if x != None:
            site = int(x)
        else:
            """There was no last-viewed site saved for this alignment, so just pick a random site."""
            site = 1
    
    save_viewing_pref(request, alib.id, con, "lastviewed_site_msa=" + msaid.__str__(), site.__str__())  
    save_viewing_pref(request, alib.id, con, "lastviewed_msaid", msaid.__str__())  
    
    return HttpResponseRedirect('/' + alib.__str__() + '/' + msaname + '/site' + site.__str__() )
    

def view_site(request, alib, con):
    """Get the model and method from the URL"""
    msaid = None
    msaname = ""
    phylomodelid = None
    phylomodelname = ""
    x = get_msamodel_from_url(request, con, msaonly=True)
    if x != None:
        (msaid, msaname, phylomodelid, phylomodelname) = x    
    
    """Get the site from the URL"""
    tokens = request.path_info.split("/")
    sitetoken = tokens[ tokens.__len__()-1 ].split(".")[0]
    site = int( re.sub("site", "", sitetoken) )
    if site < 1:
        return None
    
    save_viewing_pref(request, alib.id, con, "lastviewed_site_msa=" + msaid.__str__(), site.__str__())  
    
    
    
    cur = con.cursor()
    """Get a list of alignment methods"""
    sql = "select id, name from AlignmentMethods where id!=" + msaid.__str__()
    cur.execute(sql)
    msaid_msaname = {}
    msa_site_count = {} # key = msa, value = hash; key = site in msa, value = count of sites in msaid that map to this site
    for ii in cur.fetchall():
        id = int(ii[0])
        name = ii[1].__str__()
        msaid_msaname[id] = name
        if id not in msa_site_count:
            msa_site_count[id] = {}
    
    count_nonindel_taxa = 0
    res_count = {} # key = amino acid, value = count of occurrances
    
    leftstride=10
    while (site-leftstride) <= 0:
        leftstride -= 1
    if leftstride < 0:
        leftstride = 0
    startsite = int(site)-leftstride
    
    sql = "select taxonid, alsequence from AlignedSequences where almethod=" + msaid.__str__() + ";"
    taxonid_residue = {}  # key = taxonid, value = 3-tuple: (left flanking sequene, the residue, right flanking sequence)  
    taxonid_msa_site = {} # key = taxonid, value = hash; key = msa, value = the mapped-to site in msa
    cur.execute(sql)
    for ii in cur.fetchall():
        taxonid = ii[0]
        seq = ii[1]
        
        """Get the sequence content at, and flanking, this site"""
        #left_flank = seq[startsite-1: startsite+leftstride]
        #res = seq[startsite+leftstride]
        #right_flank = seq[startsite+leftstride+1: startsite+(2*leftstride)+2:]
        left_flank = seq[site-1-leftstride:site-1]
        res = seq[site-1]
        
        while (seq.__len__() < site+leftstride):
            leftstride -= 1
        if leftstride == 0:
            leftstride = 0
        
        right_flank = seq[site:site+leftstride]
        
        if res != "-":
            count_nonindel_taxa += 1
        if res not in res_count:
            res_count[res] = 0
        res_count[res] += 1
        
        """The residue at this site in the msa"""
        taxonid_residue[taxonid] = (left_flank, res, right_flank)
        
        """Not get the the mapped-to sites from other alignments"""
        if taxonid not in taxonid_msa_site:
            taxonid_msa_site[taxonid] = {}
        sql = "select site2, almethod2 from SiteMap where site1=" + site.__str__()
        sql += " and almethod1=" + msaid.__str__()
        sql += " and taxonid=" + taxonid.__str__()
        cur.execute(sql)
        for jj in cur.fetchall():
            site2 = jj[0]
            almethod2 = jj[1]
            taxonid_msa_site[taxonid][almethod2] = site2
            
            if site2 not in msa_site_count[almethod2]:
                msa_site_count[almethod2][site2] = 0
            msa_site_count[almethod2][site2] += 1
    
    ntaxa = taxonid_msa_site.__len__()
    
    """res tuples is a lsit of tuples for the Residue composition mini-table."""
    res_tuples = []
    last_res = None
    for res in res_count:
        res_tuples.append( (res,res_count[res]) )
        last_res = res
    
    almethods = msaid_msaname.keys()
    almethodnames = []
    for al in almethods:
        almethodnames.append(  msaid_msaname[al] )
    
    """taxonname rows is a list of tuples for the table showing the amino acid identity at each species."""
    taxonname_rows = []
    for taxonid in taxonid_residue:
        sql = "select shortname from Taxa where id=" + taxonid.__str__()
        cur.execute(sql)
        taxonname = cur.fetchone()[0]
        this_row = [ taxonname, taxonid_residue[taxonid] ]
        this_sitelist = []
        for almethod in almethods:
            if almethod in taxonid_msa_site[taxonid]:
                this_sitelist.append( (msaid_msaname[almethod], taxonid_msa_site[taxonid][almethod] ) )
            else:
                this_sitelist.append( (None,None) )
        this_row.append(this_sitelist)
        taxonname_rows.append( this_row )
    
    """Convert counts into percentages, and also format the hash as a list
        of tuples, so that the Django template language can deal with more easily."""
    msa_similarity_tuples = {}
    for msa in msa_site_count:
        msa_similarity_tuples[  msaid_msaname[msa]  ] = []
        for site2 in msa_site_count[msa]:
            this_tuple = (site2, msa_site_count[msa][site2] )
            msa_similarity_tuples[  msaid_msaname[msa]  ].append(this_tuple)


    context = get_base_context(request, alib, con)
    context["site"] = site
    context["msaname"] = msaname
    context["msaid"] = msaid
    context["taxonname_rows"] = taxonname_rows
    context["all_alignment_names"] = [msaname] + almethodnames
    context["alignment_names"] = almethodnames
    context["msa_similarity_tuples"] = msa_similarity_tuples
    context["res_tuples"] = res_tuples
    context["last_res"] = last_res
    
    return render(request, 'libview/libview_site.html', context)
    

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
    nodenumber = re.sub("Node", "", nodetoken)
    sql = "select id from Ancestors where almethod=" + msaid.__str__()
    sql += " and phylomodel=" + phylomodelid.__str__()
    sql += " and name='Node" + nodenumber.__str__() + "'"
    cur.execute(sql)
    x = cur.fetchone()
    if x == None:
        return view_library_frontpage(request, alib, con)
    ancid = x[0]

    seq = get_ml_sequence(con, ancid)

    #
    # ancid_mlseq: key = ancestor ID, value = ML sequence with gaps
    # this data will be used to compare the sequences and estimate
    # the degree of similarity of the ancestors across different
    # evolutionary models.
    #
    ancid_mlseq = {}
    all_ancids = []

    #
    # similarity_rows contain data for the table titled
    # "Similarity to Other Alignments"
    #
    similarity_rows = []
    sql = "select ancid, same_ancid from AncestorsAcrossModels where ancid=" + ancid.__str__()
    cur.execute(sql)
    for ii in cur.fetchall():
        sameancid = ii[1]
        all_ancids.append( sameancid )
        
        sql = "select name from PhyloModels where modelid in (select phylomodel from Ancestors where id=" + sameancid.__str__() + ")"
        cur.execute(sql)
        othermodelname = cur.fetchone()[0]
        
        sql = "select name from AlignmentMethods where id in (select almethod from Ancestors where id=" + sameancid.__str__() + ")"
        cur.execute(sql)
        othermsaname = cur.fetchone()[0]
        
        sql = "select name from Ancestors where id=" + sameancid.__str__()
        cur.execute(sql)
        othername = cur.fetchone()[0]
        
        this_row = (othermsaname, othermodelname, othername, sameancid )
        similarity_rows.append( this_row )
        
        this_mlseq = get_ml_sequence(con, sameancid, skip_indels=False)
        ancid_mlseq[sameancid] = this_mlseq
        
    similarity_matrix = []
    for ii in all_ancids:
        ii_mlseq = ancid_mlseq[ii]
        this_row = []
        for jj in all_ancids:
            this_row.append( ml_sequence_difference(ii_mlseq, ancid_mlseq[jj]) )
        similarity_matrix.append( this_row )


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
    context["similarity_rows"] = similarity_rows
    context["similarity_matrix"] = similarity_matrix
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

    seedtaxonid = None
    seedtaxonname = None
    taxonnames = []
    sql = "select shortname from Taxa"
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        taxonnames.append( ii[0] )
    """Get the seedsequence with indels"""
    (seedtaxonid, seedtaxonname) = get_seedtaxon(request, alib, con)
    print "1288:", seedtaxonid, seedtaxonname
    save_viewing_pref(request, alib.id, con, "lastviewed_seedtaxonid", seedtaxonid.__str__()) 
    if seedtaxonid == None:
        sql = "select shortname from Taxa"
        cur.execute(sql)
        seedtaxonname = cur.fetchone()[0]
    
    sql = "select alsequence from AlignedSequences where almethod="+ msaid.__str__() + " and taxonid in (select id from Taxa where shortname='" + seedtaxonname + "')"
    cur.execute(sql)
    x = cur.fetchone()
    seedseq = x[0]
    alignedsite_seedsite = {}
    countstates = 0
    for ii in range(0, seedseq.__len__()):
        if seedseq[ii] != "-":
            countstates += 1
            alignedsite_seedsite[ ii+1 ] = countstates
        else:
            alignedsite_seedsite[ ii+1 ] = "-"
    
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
        site_rows.append( [site,count_sites,alignedsite_seedsite[site],seedseq[site-1],tuples] )
            
    context = get_base_context(request, alib, con)
    context["node_number"] = nodenumber
    context["msaname"] = msaname
    context["modelname"] = phylomodelname
    context["site_rows"] = site_rows
    context["seedtaxonname"] = seedtaxonname
    context["taxonnames"] = taxonnames
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

    """Save this viewing preference -- it will load automatically next time
        the user comes to the ancestors page."""
    save_viewing_pref(request, alib.id, con, "lastviewed_msaid", msaid.__str__())        
    save_viewing_pref(request, alib.id, con, "lastviewed_modelid", phylomodelid.__str__()) 

    taxonnames = []
    sql = "select shortname from Taxa"
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        taxonnames.append( ii[0] )

    """Get the seedsequence with indels"""
    (seedtaxonid, seedtaxonname) = get_seedtaxon(request, alib, con)
    print "1358:", seedtaxonid, seedtaxonname
    save_viewing_pref(request, alib.id, con, "lastviewed_seedtaxonid", seedtaxonid.__str__()) 
    seedsequence = get_sequence_for_taxon(con, msaname, seedtaxonid)
    nsites = seedsequence.__len__()

    sl = seedtaxonname.__len__()
    if sl > 10:
        seedtaxonnameshort = seedtaxonname[0:4] + "..." + seedtaxonname[sl-7:sl]
    else:
        seedtaxonnameshort = seedtaxonname
    
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
    
    """For some reason, the ancestors weren't selected in the HTML form 
        (or this is the first time rendering) so let's check if the user has 
        any saved preferences about the last-viewed ancestors."""
    if ancid1 == None or ancid2 == None:
        last_viewed_ancid1 = get_viewing_pref(request, alib.id, con, "lastviewed_ancid1_msa=" + msaid.__str__() )
        last_viewed_ancid2 = get_viewing_pref(request, alib.id, con, "lastviewed_ancid2_msa=" + msaid.__str__() )
        if last_viewed_ancid1 != None:
            ancid1 = int(last_viewed_ancid1)
            sql = "select name from Ancestors where id=" + ancid1.__str__()
            cur.execute(sql)
            ancname1 = cur.fetchone()[0]
        if last_viewed_ancid2 != None:
            ancid2 = int(last_viewed_ancid2)
            sql = "select name from Ancestors where id=" + ancid2.__str__()
            cur.execute(sql)
            ancname2 = cur.fetchone()[0]
        
    """OK, the ancestors are still None. Deal with this by 
    just grabbing the first ancestor from the database"""
    if ancid1 == None or ancid2 == None:
        sql = "select name, id from Ancestors where almethod=" + msaid.__str__() + " and phylomodel=" + phylomodelid.__str__()
        cur.execute(sql)
        x = cur.fetchall()
        if x == None:
            write_error(con, "I can't find the ancestor in the database for " + msaid.__str__() + " and " + phylomodelid.__str__() )
        ancid1 = int(x[0][1])
        ancname1 = x[0][0]
        ancid2 = int(x[1][1])
        ancname2 = x[1][0]
    
    save_viewing_pref(request, alib.id, con, "lastviewed_ancid1_msa=" + msaid.__str__(), ancid1) 
    save_viewing_pref(request, alib.id, con, "lastviewed_ancid2_msa=" + msaid.__str__(), ancid2)

    """Get the site map beween different sequence alignments"""
    msa_site1_site2 = {} # key = msaid, value = hash; key = site in user-specified msa, value = site in msaid
    sql = "select id, name from AlignmentMethods"
    cur.execute(sql)
    msaid_name = {}
    for ii in cur.fetchall():
        this_msaid = int(ii[0])
        this_msaname = ii[1].__str__()
        msaid_name[ this_msaid ] = this_msaname
        msa_site1_site2[this_msaid] = {}
        
        """For each alignment method, get the mapped-to sites from the SiteMap table."""
        sql = "select site1, site2 from SiteMap where"
        sql += " almethod1=" + msaid.__str__() # the user-specified alignment method
        sql += " and almethod2=" + ii[0].__str__()
        sql += " and taxonid=" + seedtaxonid.__str__()
        cur.execute(sql)
        query = cur.fetchall()
        for qq in query:
            site1 = qq[0]
            site2 = qq[1]
            msa_site1_site2[this_msaid][site1] = site2      
    """Note: at this point,  msa_site1_site2 contains data about all alignments EXCEPT
        for the user-specified msaid"""

    """ Get a list of these ancestors in other alignments and models """ 
    print "1448:", ancid1, ancid2
    matched_ancestors = get_ancestral_matches(con, ancid1, ancid2)
    print "1449:", matched_ancestors
    matched_ancestors = [ (ancid1,ancid2) ] + matched_ancestors
     
    ancid_msaid = {}
    ancid_model = {}
    ancid_site_state_pp = {}
    ancid_name = {}    
    ancid_site_statepp = {}
    for match in matched_ancestors:
        for id in [ match[0], match[1] ]:
            sql = "Select almethod, phylomodel, name from Ancestors where id=" + id.__str__()
            cur.execute(sql)
            x = cur.fetchone()
            ancid_msaid[id] = int(x[0])
            ancid_model[id] = int(x[1])
            ancname = x[2]
            ancid_name[id] = ancname
            #msaname = msaid_name[ ancid_msaid[id] ]
            ancid_site_statepp[id] = get_site_ml(con, id, skip_indels = False)   

    """We need model names and alignment names for printing in the mutation table header rows."""
    phylomodelid_name = {}
    sql = "select modelid, name from PhyloModels"
    cur.execute(sql)
    query = cur.fetchall()
    for ii in query:
        phylomodelid_name[   ii[0]  ] = ii[1]
               
    mutation_header = []
    mutation_rows = []
    mutation_shortlist = [] # each item is a tuple: (site in msa, site in seed, ancestral state 1, anc. state 2, weight)
    seed_site = 0 # the index into the seed sequence sans indels
    """For each site in the seed sequence"""
    for site in range(1, nsites+1):
        found_content = False # did we find any non-indel characters?
        this_row = []

        
        if site == 1:
            """Add header information"""
            mutation_header = ["Site in " + msaname]
            mutation_header.append( "Site in\n" + seedtaxonnameshort )

        if seedsequence[site-1] != "-":
            seed_site += 1
            display_seed_site = seed_site
        else:
            display_seed_site = "-"

        count_replicates = 0 # how many of the columns support this mutation?
        focus_state1 = None
        focus_state2 = None
        
        """For each ancestor"""
        for match in matched_ancestors:
            #print "988:", match
            this_anc1 = match[0]
            this_anc2 = match[1]
            
            this_msaid1 = ancid_msaid[this_anc1]
            this_msaid2 = ancid_msaid[this_anc2]
            
            this_msaname1 = msaid_name[this_msaid1]
            this_msaname2 = msaid_name[this_msaid2]
            
            this_modelid1 = ancid_model[this_anc1]
            this_modelid2 = ancid_model[this_anc2]
            
            this_modelname1 = phylomodelid_name[this_modelid1]
            this_modelname2 = phylomodelid_name[this_modelid2]
            
            if this_modelid1 != this_modelid2:
                continue
            if this_msaid1 != this_msaid2:
                continue

            if site == 1:
                """Add header information"""
                mutation_header.append( this_modelname1 + "\n" + this_msaname1 )
  
            site2 = None
            if int(this_msaid1) == int(msaid):
                site2 = site
            elif seedsequence[site-1] != "-":
                """Get a mapped site"""
                if site in msa_site1_site2[this_msaid1]:
                    site2 = msa_site1_site2[this_msaid1][site]

            this_column = ("","","","","", "") # Six values for the Django template to use. see the line down below starting with this_column = (
            if site2 != None:
                (anc1state, anc1pp) = ancid_site_statepp[this_anc1][site2]
                (anc2state, anc2pp) = ancid_site_statepp[this_anc2][site2]
                mutation_flag = ""
                if anc1state != "-" or anc2state != "-":
                    found_content = True
                if anc1state == "-" and anc2state != "-":
                    mutation_flag = "i"
                elif anc2state == "-" and anc1state != "-":
                    mutation_flag = "d"
                elif anc1state != anc2state and anc1pp > 0.7 and anc2pp > 0.7:
                    mutation_flag = "1"
                elif anc1state != anc2state and anc1pp > 0.5 and anc2pp > 0.5:
                    mutation_flag = "2"
                elif anc1state != anc2state and anc1pp > 0.4 and anc2pp > 0.4:
                    mutation_flag = "3"
                    
                if mutation_flag in ["1", "2", "3"]:
                    count_replicates += 1
                    
                this_column = ( anc1state, anc1pp.__str__(), anc2state, anc2pp.__str__(), mutation_flag, site2)
            
                if ancid1 == this_anc1 and ancid2 == this_anc2:
                    focus_state1 = anc1state
                    focus_state2 = anc2state
            
            this_row.append(  this_column  )
        if found_content == True:
            mutation_rows.append( (site, seed_site, seedsequence[site-1], this_row) )
    
        """This classifies as 'strong' support"""
        #if count_replicates > ( phylomodelid_name.keys().__len__()-1):
        #if count_replicates > 2:
        if focus_state1 != focus_state2 and count_replicates > 2:
            (anc1state, anc1pp) = ancid_site_statepp[ matched_ancestors[0][0] ][site]
            (anc2state, anc2pp) = ancid_site_statepp[ matched_ancestors[0][1] ][site]
            tuple = (site, display_seed_site, anc1state, anc2state, count_replicates)
            mutation_shortlist.append( tuple )
    
    context["mutation_header"] = mutation_header
    context["mutation_rows"] = mutation_rows
    context["mutation_shortlist"] = mutation_shortlist

    """Save this viewing preference -- it will load automatically next time
        the user comes to the ancestors page."""
    save_viewing_pref(request, alib.id, con, "lastviewed_msaid", msaid.__str__())        
    save_viewing_pref(request, alib.id, con, "lastviewed_modelid", phylomodelid.__str__()) 

    sql = "select name, id from Ancestors where almethod=" + msaid.__str__() + " and phylomodel=" + phylomodelid.__str__()
    cur.execute(sql)
    x = cur.fetchall()
    context["ancnames"] = []
    for ii in x:
        context["ancnames"].append( ii[0] )
    context["seedtaxonname"] = seedtaxonname
    context["taxonnames"] = taxonnames
    context["msanames"] = get_alignmentnames(con)
    context["modelnames"] = get_modelnames(con)
    context["default_msaname"] = msaname
    context["default_modelname"] = phylomodelname
    context["default_ancname1"] = ancname1
    context["default_ancname2"] = ancname2

    return render(request, 'libview/libview_mutations_branch.html', context)

