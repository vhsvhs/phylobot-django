import os, sys
from phylobot.models import *
from django.core.exceptions import ObjectDoesNotExist

def get_modelnames(con):
    cur = con.cursor()
    modelnames = []
    sql = "select name from PhyloModels"
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        modelnames.append( ii[0] )
    return modelnames

def get_alignmentnames(con):
    cur = con.cursor()
    sql = "select name from AlignmentMethods"
    cur.execute(sql)
    x = cur.fetchall()
    msanames = []
    for ii in x:
        msanames.append( ii[0] )
    return msanames

def __get_msamodel_from_url(request, con):
    """Returns a tuple, with the ID of the alignment method and 
        the ID of the phylo. model, interpreted from the URL.
        Assumes URLs formatted as "..../msa_method.phylomodel/X
        This is a helper method for the function named get_msamodel"""
    cur = con.cursor()
    
    msaname = None
    msaid = None
    modelname = None
    modelid = None
    
    tokens = request.path_info.split("/")
    datatoken = tokens[  tokens.__len__()-2  ]
    tokens = datatoken.split(".")
    if tokens.__len__() < 2:
        return None
    msaname = tokens[0]
    phylomodelname = tokens[1]
    sql = "select id from AlignmentMethods where name='" + msaname.__str__() + "'"
    cur.execute(sql)
    msaid = cur.fetchone()
    if msaid == None:
        """I can't find this alignment method in the database"""
        return None
    msaid = msaid[0]
    
    sql = "select modelid from PhyloModels where name='" + phylomodelname.__str__() + "'"
    cur.execute(sql)
    phylomodelid = cur.fetchone()
    if phylomodelid == None:
        """I can't find this model in the database."""
        return None
    phylomodelid = phylomodelid[0]
    
    return (msaid, msaname, phylomodelid, phylomodelname)

def save_viewing_pref(request, alib, con, keyword, value):
    """Save a viewing preference so that it can be loaded automatically next time
        the user views the same page.
        If this method fails, it just returns without error."""
    user = request.user
    query = ViewingPrefs.objects.filter(user=user, libid=alib.id, keyword=keyword)
    if query.__len__() == 0:
        """Create a new preference entry"""
        pref = ViewingPrefs(user=user, libid=alib.id, keyword=keyword, value=value)
    else:
        """An entry already exists. Overwrite it."""
        pref = query[0]
        pref.value = value
    pref.save()

def get_viewing_pref(request, alib, con, keyword):
    """Returns the value for a saved viewing preference 'keyword', 
        or None if the preference entry doesn't exist."""
    user = request.user
    query = ViewingPrefs.objects.filter(user=user, libid=alib.id, keyword=keyword)
    if query.__len__() == 0:
        return None
    else:
        pref = query[0]
        return pref.value
    
def __get_msa_from_post(request, con):
    """Returns (msaname, msaid) from POST form value named 'msaname'"""
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
    """Returns the tuple containing (modelname, modelid) from a POST form value named 'modelname'
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
        x = __get_msamodel_from_url(request, con)
        if x != None:
            (msaid, msaname, phylomodelid, phylomodelname) = x

    """INPUT 3: maybe the user has some saved viewing preferences?"""
    if msaid == None and phylomodelid == None:
        msaid = get_viewing_pref(request, alib, con, "lastviewed_msaid")
        phylomodelid = get_viewing_pref(request, alib, con, "lastviewed_modelid")
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

def get_seed_sequence(con, msaname):
    cur = con.cursor()
    sql = "select id from Taxa where shortname in (select value from Settings where keyword='seedtaxa')"
    cur.execute(sql)
    seedtaxonid = cur.fetchone()[0]
    
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
    return newick

def get_list_of_same_ancids(con, ancid):
    """Return a list of other ancestors, from other alignments and models, that share the same ingroup position
        as the ancestor reference by ancid"""
    sql = "select "
    
    #newick = reroot_newick(con, newick)
    

#
# depricated -- all the tree re-rooting should
#                 occur in the ASR pipeline before it's placed in the database.
#
# def reroot_newick(con, newick):
#     """Provide a newick string, this method will re-root the tree
#         based on the 'outgroup' setting."""
#     cur = con.cursor()
#     dendrotree = Tree()
#     dendrotree.read_from_string(newick, "newick")
#     sql = "select shortname from Taxa where id in (select taxonid from GroupsTaxa where groupid in (select id from TaxaGroups where name='outgroup'))"
#     cur.execute(sql)
#     rrr = cur.fetchall()
#     outgroup_labels = []
#     for iii in rrr:
#         outgroup_labels.append( iii[0].__str__() )
#     mrca = dendrotree.mrca(taxon_labels=outgroup_labels)
#     dendrotree.reroot_at_edge(mrca.edge, update_splits=True)
#     newick = dendrotree.as_string("newick")
#     return newick