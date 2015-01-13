import os
from django import forms
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.template import RequestContext, Context, loader

from phylobot.models import *

import sqlite3 as sqlite

import logging
logger = logging.getLogger(__name__)

def view_library(request, libid):
    
    print "19:", request.path_info
    print "20", libid
    
    """If a completed ancestral library exists whose name or ID is libid, then
        this method will lead to a view into that library."""
    if libid == None:
        print ". no libid was provided."
    
    """Does libid exist in our known libraries?"""
    foundit = False
    for anclib in AncestralLibrary.objects.all():
        print "27:", libid, anclib.id
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
    
    if request.path_info.endswith("alignments"):
        pass
    elif request.path_info.endswith("trees"):
        pass
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
        logger.error("I cnanot find the AncestralLibrary SQL database at " + dbpath)
        return None
    con = sqlite.connect( dbpath )  
    return con


def view_library_frontpage(request, alib, con):    
    cur = con.cursor()
    
    """Fill the context with stuff that's needed for the HTML template."""
    context = {}
    context["alid"] = alib.id
    
    sql = "select value from Settings where keyword='project_title'"
    cur.execute(sql)
    context["library_name"] = cur.fetchone()[0]
    
    x = alib.contact_authors_profile.all()
    context["contact_authors"] = x
    
    return render(request, 'libview/libview_frontpage.html', context)