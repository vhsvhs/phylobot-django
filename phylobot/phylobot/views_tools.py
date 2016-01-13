import os, re, sys
from phylobot.models import *
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render

import logging
logger = logging.getLogger(__name__)

def get_modelnames(con):
    cur = con.cursor()
    modelnames = []
    sql = "select name from PhyloModels"
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        modelnames.append( ii[0] )
    return modelnames

def get_modelids(con):
    cur = con.cursor()
    ids = []
    sql = "select modelid from PhyloModels"
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        ids.append( ii[0] )
    return ids

def get_alignmentnames(con):
    cur = con.cursor()
    sql = "select name from AlignmentMethods"
    cur.execute(sql)
    x = cur.fetchall()
    msanames = []
    for ii in x:
        msanames.append( ii[0] )
    return msanames

def get_alignmentids(con):
    cur = con.cursor()
    sql = "select id from AlignmentMethods"
    cur.execute(sql)
    x = cur.fetchall()
    ids = []
    for ii in x:
        ids.append( ii[0] )
    return ids

def get_alignment_name_for_id(con, id):
    cur = con.cursor()
    sql = "select name from AlignmentMethods where id=" + id.__str__()
    cur.execute(sql)
    return cur.fetchone()[0]

def get_model_name_for_id(con, id):
    cur = con.cursor()
    sql = "select name from PhyloModels where modelid=" + id.__str__()
    cur.execute(sql)
    return cur.fetcheone()[0]

def get_msamodel_from_url(request, con, msaonly=False):
    """Returns a tuple, with the ID of the alignment method and 
        the ID of the phylo. model, interpreted from the URL.
        Assumes URLs formatted as "..../msa_method.phylomodel/..."
        or formatted as "..../msa_method/...."
        This is a helper method for the function named get_msamodel"""
    cur = con.cursor()
    
    msaname = None
    msaid = None
    phylomodelname = None
    phylomodelid = None
        
    tokens = request.path_info.split("/")
    
    """datatoken may be <alignment>.<model> or just <alignment>"""
    datatoken = tokens[  tokens.__len__()-2  ]
    tokens = datatoken.split(".")

    if msaonly == False and tokens.__len__() < 2:
        """Then this token doesn't contain an msa.model"""
        return None

    msaname = tokens[0].__str__()
    sql = "select id from AlignmentMethods where name='" + msaname.__str__() + "'"
    cur.execute(sql)
    msaid = cur.fetchone()
    if msaid == None:
        """I can't find this alignment method in the database"""
        print >> sys.stderr, "Warning 50: I cannot find the alignment method " + msaname + " in the database."
        return None
    msaid = msaid[0]

    if tokens.__len__() == 2:
        """The URL looks like .../msaname.modelname/..., then get the model name too"""
        phylomodelname = tokens[1].__str__()    
        sql = "select modelid from PhyloModels where name='" + phylomodelname.__str__() + "'"
        cur.execute(sql)
        phylomodelid = cur.fetchone()
        if phylomodelid == None:
            """I can't find this model in the database."""
            return None
        phylomodelid = phylomodelid[0]
    
    return (msaid, msaname, phylomodelid, phylomodelname)

def save_viewing_pref(request, alibid, con, keyword, value):
    """Save a viewing preference so that it can be loaded automatically next time
        the user views the same page.
        If this method fails, it just returns without error."""
    user = request.user
    """Deal with users that aren't signed in"""    
    if user.is_anonymous():
        return
    query = ViewingPrefs.objects.filter(user=user, libid=int(alibid), keyword=keyword)
    if query.__len__() == 0:
        """Create a new preference entry"""
        pref = ViewingPrefs(user=user, libid=alibid, keyword=keyword, value=value)
    else:
        """An entry already exists. Overwrite it."""
        pref = query[0]
        pref.value = value
    pref.save()

def get_viewing_pref(request, alibid, con, keyword):
    """Returns the value for a saved viewing preference 'keyword', 
        or None if the preference entry doesn't exist."""
    user = request.user
    
    """Deal with users that aren't signed in"""    
    if user.is_anonymous():
        return None
        
    query = ViewingPrefs.objects.filter(user=user, libid=alibid, keyword=keyword)
    if query.__len__() == 0:
        return None
    else:
        pref = query[0]
        return pref.value
    
def __get_msa_from_post(request, con):
    """Returns the msaname from POST form containing the field named 'msaname'"""
    if "msaname" in request.POST:
        cur = con.cursor()
        msaname = request.POST.get("msaname")
        sql = "select name, id from AlignmentMethods where name='" + msaname + "'"
        cur.execute(sql)
        x = cur.fetchone()
        if x != None:
            msaid = x[1]
            return (msaname, msaid)
    return None

def __get_model_from_post(request, con):
    """Returns the modelid from a POST form value named 'modelname'
        If the form lacks a field named 'modelname', then this method returns None.
        This is a helper method for get_msamodel"""
    if "modelname" in request.POST:
        cur = con.cursor()
        phylomodelname = request.POST.get("modelname")
        sql = "select name, modelid from PhyloModels where name='" + phylomodelname + "'"
        cur.execute(sql)
        x = cur.fetchone()
        if x != None:
            phylomodelid = x[1]
            return (phylomodelname, phylomodelid)
    return None

def __get_seedtaxon_from_post(request, con):
    """Returns the tuple (taxon ID, taxon name), where taxon name was read
        from the request POST form field named 'seedtaxonname'
        If the request lacks a field named 'seedtaxonname', then this method returns None."""
    if "seedtaxonname" in request.POST:
        cur = con.cursor()
        seedtaxonname = request.POST.get("seedtaxonname")
        sql = "select id, shortname from Taxa where shortname='" + seedtaxonname + "'"
        cur.execute(sql)
        x = cur.fetchone()
        if x == None:
            return None
        taxonid = x[0]
        return (taxonid, seedtaxonname)
    return None

def get_seedtaxon(request, alib, con):
    """This method returns the seed taxon, by searching in a few different places
        for information. See the related method get_msamodel"""
    cur = con.cursor()
    seedtaxonname = None
    seedtaxonid = None

    """INPUT 1: parse the POST information from the web form"""
    if request.method == "POST":
        if "seedtaxonname" in request.POST:
            (seedtaxonid, seedtaxonname) = __get_seedtaxon_from_post(request, con)
            print "161:", seedtaxonid, seedtaxonname

    """INPUT 3: maybe the user has some saved viewing preferences?"""
    if seedtaxonid == None:
        seedtaxonid = get_viewing_pref(request, alib.id, con, "lastviewed_seedtaxonid")
        if seedtaxonid != None:
            sql = "select shortname from Taxa where id=" + seedtaxonid.__str__()
            cur.execute(sql)
            seedtaxonname = cur.fetchone()[0]
            
    """INPUT 4: pick a random sequence to tbe the seed."""
    if seedtaxonid == None:
        sql = "select id, shortname from Taxa"
        cur.execute(sql)
        x = cur.fetchone()
        seedtaxonid = x[0]
        seedtaxonname = x[1]

    return (seedtaxonid, seedtaxonname)

def get_msamodel(request, alib, con):
    """This method returns the tuple (msaid, msaname, phylomodelid, phylomodelname) by parsing
        data from several possible different sources, in this order:
            1. an HTML POST, where the msaname and modelname are fields in the HTML form.
            2. the URL, with a format like this: .../mafft.PROTCATLG/ancestors
            3. previously-saved user preferences, i.e. the last-viewed alignment and model.
            4.  (default) the first alignment amodel in the database."""
    cur = con.cursor()
    
    msaname = None
    msaid = None
    phylomodelname = None
    phylomodelid = None
    
    """We need to determine the alignment method and phylo. model.
        There are several places this information may be found...."""
        
    """INPUT 1: parse the POST information from the web form"""
    if request.method == "POST":
        if "msaname" in request.POST:
            (msaname, msaid) = __get_msa_from_post(request, con)
        if "modelname" in request.POST:
            (phylomodelname, phylomodelid) = __get_model_from_post(request, con)
    
    """INPUT 2: parse a URL like .../mafft.PROTCATLG/ancestors"""
    if msaid == None and phylomodelid == None:
        x = get_msamodel_from_url(request, con)
        if x != None:
            (msaid, msaname, phylomodelid, phylomodelname) = x
            
    """INPUT 3: maybe the user has some saved viewing preferences?"""
    if msaid == None and phylomodelid == None:
        msaid = get_viewing_pref(request, alib.id, con, "lastviewed_msaid")
        phylomodelid = get_viewing_pref(request, alib.id, con, "lastviewed_modelid")
        if msaid != None:
            sql = "select name from AlignmentMethods where id=" + msaid.__str__()
            cur.execute(sql)
            msaname = cur.fetchone()[0]
        if phylomodelid != None:
            sql = "select name from PhyloModels where modelid=" + phylomodelid.__str__()
            cur.execute(sql)
            phylomodelname = cur.fetchone()[0]

    """"INPUT 4: no alignment and model were specified, so just pick some random values to initialize the page."""
    if msaid == None:
        sql = "select name, id from AlignmentMethods"
        cur.execute(sql)
        x = cur.fetchone()
        msaid = x[1]
        msaname = x[0]
    if phylomodelid == None:
        sql = "select name, modelid from PhyloModels"
        cur.execute(sql)
        x = cur.fetchone()
        phylomodelid = x[1]
        phylomodelname = x[0] 
    
    return (msaid, msaname, phylomodelid, phylomodelname)       

def get_sequence_for_taxon(con, msaname, seedtaxonid):
    cur = con.cursor()
    
    sql = "select id from AlignmentMethods where name='" + msaname + "'"
    cur.execute(sql)
    msaid = cur.fetchone()[0]
    
    sql = "select alsequence from AlignedSequences where almethod=" + msaid.__str__() + " and taxonid=" + seedtaxonid.__str__() 
    cur.execute(sql)
    seedsequence = cur.fetchone()[0]
    return seedsequence 

def get_anc_cladogram(con, msaid, phylomodelid):
    """Returns the Newick-formatted string with the cladogram of ancestral
        nodes for the given alignment method (msaid) and model (phylomodelid)"""
    cur = con.cursor()
    sql = "select newick from AncestralCladogram where unsupportedmltreeid in"
    sql += "(select id from UnsupportedMlPhylogenies where almethod=" + msaid.__str__() + " and phylomodelid=" + phylomodelid.__str__() + ")"
    cur.execute(sql)
    newick = cur.fetchone()[0]
    newick = newick.__str__()
    newick = re.sub("\[.*\]", "", newick)
    return newick

def get_list_of_same_ancids(con, ancid):
    """Return a list of other ancestors, from other alignments and models, that share the same ingroup position
        as the ancestor reference by ancid"""
    cur = con.cursor()
    sql = "select same_ancid from AncestorsAcrossModels where ancid=" + ancid.__str__()
    cur.execute(sql)
    matches = []
    msa_model_match = {}
    for ii in cur.fetchall():
        this_ancid = ii[0]
        sql = "select almethod, phylomodel from Ancestors where id=" + this_ancid.__str__()
        cur.execute(sql)
        xx = cur.fetchone()
        almethod = xx[0]
        phylomodelid = xx[1]
        if almethod not in msa_model_match:
            msa_model_match[almethod] = {}
        msa_model_match[almethod][phylomodelid] = this_ancid
    
    """Get the alignment method of the user-specificid ancid.
        Make a list of all alignment methods. Pop out the user-spec. method,
        and then sort the remaining methods.
        Finally, list the ancestral matches in the order of first those matches
        with the same alignment as the user-spec. alignment, and then second
        those matches from the other alignments."""
    sql = "Select almethod from Ancestors where id=" + this_ancid.__str__()
    cur.execute(sql)
    input_almethod = cur.fetchone()[0]
    
    almethods = msa_model_match.keys()
    almethods.sort()
    almethods.pop(  almethods.index(input_almethod)  )
    
    for model in msa_model_match[input_almethod]:
        matches.append( msa_model_match[input_almethod][model] )
    for alid in almethods:
        for model in msa_model_match[alid]:
            matches.append( msa_model_match[alid][model] )
    return matches


def get_ancestral_matches(con, ancid1, ancid2):
    
    #print "269:", ancid1, ancid2
    
    cur = con.cursor()
    sql = "select same_ancid from AncestorsAcrossModels where ancid=" + ancid1.__str__()
    cur.execute(sql)
    
    msas = [] # a list of msa ids
    models = [] # a list of phylomodel ids
    
    msa_model_match1 = {} # key = msa, value = hash; key = model, value = ancestral ID of a match to ancid1
    for ii in cur.fetchall():
        this_ancid = ii[0]
        sql = "select almethod, phylomodel from Ancestors where id=" + this_ancid.__str__()
        cur.execute(sql)
        xx = cur.fetchone()
        almethod = xx[0]
        if almethod not in msas:
            msas.append(almethod)
        phylomodelid = xx[1]
        if phylomodelid not in models:
            models.append(phylomodelid)
        if almethod not in msa_model_match1:
            msa_model_match1[almethod] = {}
        msa_model_match1[almethod][phylomodelid] = this_ancid
    
    
    sql = "select same_ancid from AncestorsAcrossModels where ancid=" + ancid2.__str__()
    cur.execute(sql)
    msa_model_match2 = {}# key = msa, value = hash; key = model, value = ancestral ID of a match to ancid2
    for ii in cur.fetchall():
        this_ancid = ii[0]
        sql = "select almethod, phylomodel from Ancestors where id=" + this_ancid.__str__()
        cur.execute(sql)
        xx = cur.fetchone()
        almethod = xx[0]
        if almethod not in msas:
            msas.append(almethod)
        phylomodelid = xx[1]
        if phylomodelid not in models:
            models.append(phylomodelid)
        if almethod not in msa_model_match2:
            msa_model_match2[almethod] = {}
        msa_model_match2[almethod][phylomodelid] = this_ancid    
    
    """Now find those alignment-model combinations with a match to both anc1 and anc2"""
    sql = "Select almethod from Ancestors where id=" + ancid1.__str__()
    cur.execute(sql)
    input_almethod = cur.fetchone()[0]
    
    #print "319:", msas
    #print "360:", models
    if msas.__len__() == 0:
        """msas can be empty if the user considered only one alignment/model combo"""
        return []
    
    # removed december 2015
    #msas.pop( msas.index(input_almethod) )
    
    matches = []
    #if input_almethod in msa_model_match1 and input_almethod in msa_model_match2:
    #    for model in models:
    #        if model in msa_model_match1[input_almethod] and model in msa_model_match2[input_almethod]:
    #            matches.append( (msa_model_match1[input_almethod][model], msa_model_match2[input_almethod][model]) )        
    #else:
    #    print >> sys.stderr, "Error 296 (view_tools.py) " +  input_almethod.__str__() + " " + msa_model_match1.keys().__str__() + " " + msa_model_match2.keys().__str__()
        
    for msa in msas:
        if msa in msa_model_match1 and msa in msa_model_match2:
            for model in models:
                if model in msa_model_match1[msa] and model in msa_model_match2[msa]:
                    matches.append( (msa_model_match1[msa][model], msa_model_match2[msa][model]) )
    
    return matches



