import os, sys
from phylobot.models import *
from django.core.exceptions import ObjectDoesNotExist

def get_msa_and_model(request, con):
    """Returns a tuple, with the ID of the alignment method and 
        the ID of the phylo. model, interpreted from the URL.
        Assumes URLs formatted as "..../msa_method.phylomodel/X"""
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
    
    
    