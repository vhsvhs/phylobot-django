import os
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

import logging
logger = logging.getLogger(__name__)

def view_library(request, libid):
        
    """If a completed ancestral library exists whose name or ID is libid, then
        this method will lead to a view into that library."""
    if libid == None:
        print ". no libid was provided."
    
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
    print "36:", alib
    
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
    elif request.path_info.endswith("mutations"):
        pass
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
    print "\n. 104: connecting to DB:", dbpath
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
        print "154:", sql
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
            print sql

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
        print "277:", sql
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
        print sql
        count = cur.fetchone()
        #print "205:", count
        count = count[0]
        #print "207:", count
        msaid_ntaxa[msaid] = count 
        sql = "select length(alsequence) from AlignedSequences where almethod=" + msaid.__str__()
        cur.execute(sql)
        length = cur.fetchone()
        print "209:", length
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
    context = get_base_context(request, alib, con) 
    msaname = None
    msaid = None
    phylomodelname = None
    phylomodelid = None
    
    tokens = request.path_info.split(".")
    if tokens.__len__() > 2:
        msaname = tokens[ tokens.__len__()-3]
        sql = "select id from AlignmentMethods where name='" + msaname.__str__() + "'"
        cur.execute(sql)
        msaid = cur.fetchone()
        if msaid == None:
            return view_library_frontpage(request, alib, con)
        msaid = msaid[0]
        
        phylomodelname = tokens[ tokens.__len__()-2 ]        
        sql = "select modelid from PhyloModels where name='" + phylomodelname.__str__() + "'"
        cur.execute(sql)
        phylomodelid = cur.fetchone()
        if phylomodelid == None:
            return view_library_frontpage(request, alib, con)
        phylomodelid = phylomodelid[0]
    
    if msaid == None:
        sql = "select name, id from AlignmentMethods"
        cur.execute(sql)
        x = cur.fetchone()
        msaname = x[0]
        msaid = x[1]
    if phylomodelid == None:
        sql = "select name, modelid from PhyloModels"
        cur.execute(sql)
        x = cur.fetchone()
        phylomodelname = x[0]
        phylomodelid = x[1]
        
        
    context["msaname"] = msaname
    context["phylomodelname"] = phylomodelname
    
    cladogramstring = ""
    sql = "select newick from AncestralCladogram where unsupportedmltreeid in"
    sql += "(select id from UnsupportedMlPhylogenies where almethod=" + msaid.__str__() + " and phylomodelid=" + phylomodelid.__str__() + ")"
    cur.execute(sql)
    newick = cur.fetchone()[0]
    
    """This following block will fetch the XML string for use with the javascript-based
        phylogeny viewer.
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
    urlprefix = alib.id.__str__() + "/" + msaname + "." + phylomodelname
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
    
    sql = "select name from PhyloModels"
    cur.execute(sql)
    x = cur.fetchall()
    modelnames = []
    for ii in x:
        modelnames.append( ii[0] )
    context["modelnames"] = modelnames
    
    return render(request, 'libview/libview_anctrees.html', context)