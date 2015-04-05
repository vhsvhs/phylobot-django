from datetime import datetime
import random, subprocess

from django.conf import settings
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, Context, loader
from django.contrib.auth.decorators import login_required

from portal.models import *
from portal.forms import *
from portal.tools import *

from aws_tools import *

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps
    
def get_mr_seqfile(request):
    lastjob = get_mr_job(request)
    return lastjob.settings.original_aa_file
    
    """Returns the most-recently modified sequence file."""
    # Get the file that was most recently uploaded
    files = SeqFile.objects.filter(owner=request.user)
    newestfile = None
    for f in files:
        if newestfile == None:
            newestfile = f
        elif newestfile.timestamp_uploaded < f.timestamp_uploaded:
            newestfile = f
    return newestfile

def get_mr_genefamily(request):
    lastjob = get_mr_job(request)
    return lastjob.settings.genefamily
    
    """Returns the most-recently modified gene family."""
    genefams = GeneFamily.objects.filter(owner=request.user)
    last_genefam = None
    for g in genefams:
        if last_genefam == None:
            last_genefam = g
        elif last_genefam.last_modified < g.last_modified:
            last_genefam = g  
    return last_genefam

def get_mr_job(request):
    """Returns the most-recently modified gene family."""
    jobs = Job.objects.filter(owner=request.user)
    last_job = None
    for j in jobs:
        if last_job == None:
            last_job = j
        elif last_job.last_modified < j.last_modified:
            last_job = j  
    return last_job


def kill_orphan_jobs(request):
    """Remove any jobs that were started to be composed, but not completed."""
    orphans = Job.objects.filter(owner=request.user)
    for o in orphans:
        if o.settings == None:
            continue
        if o.settings.name == None or o.settings.original_aa_file == None:
            o.settings.delete()
            o.delete()

def is_valid_fasta(path, is_uniprot=False):
    """This method checks if the FASTA file located at 'path' is a valid FASTA format.
        If there are formatting problems, this method will attempt to fix them (i.e., /r line breaks
        instead of \n line break. If the problems cannot be fixed, then this message will
        return an error.
        
        At the end of checking, this message returns the tuple (flag, message), 
        where flag can be True/False and message is an error message (i.e. a string) if flag==False.
    """

    msg = None    
    if os.path.exists(path) == False or path == None:
        msg = "An error occurred when uploading your file. Please try again."
        return (False, msg)

    taxa_seq = get_taxa(path, "fasta") 

    for taxa in taxa_seq:
        if taxa.split(">").__len__() > 2:
            msg = "Your sequence named '" + taxa + "' appears to be two sequence names combined. Can you correct this?"
            return (False, msg)
        if taxa_seq[taxa].__len__() == 0:
            msg = "Your sequence named '" + taxa + "' doesn't appear to contain any sequence content."
            return (False, msg)
        if is_uniprot:
            tokens = taxa.split("|")
            if tokens.__len__() < 2:
                msg = "Your sequence name '" + taxa + "' doesn't appear to be the NCBI/UniProtKB format. Are you sure you're using the UniProt format? If not, please uncheck the box."
                return (False, msg)

    """Check for correct line breaks -- problems can occur in the FASTA file
        if it was created in Word, or rich text."""
    if taxa_seq.__len__() < 3:
        msg = "Something is wrong with your FASTA file. It doesn't appear to contain enough sequences. Check your line breaks. Did you create this FASTA file in Word, or some other rich text editor?"
        return (False, msg)

    """This preliminary check seems to indicate the FASTA file is OK."""
    return (True, None)

def write_clean_fasta(taxa_seq, outpath):
    fout = open(outpath, "w")
    for taxa in taxa_seq:
        fout.write(">" + taxa + "\n")
        fout.write( taxa_seq[taxa] + "\n")
    fout.close()

def parse_uniprot_seqname(name):
    """This method will attempt to get the UniProtKB / NCBI values from a sequence name.
        It assumes that we've already established that this sequence name has at least three tokens
        when split with | """
    tokens = name.split("|")
    db = tokens[0]
    uniqueid = tokens[1]
    entryname = tokens[2]
    subtok = ""
    if tokens[4].startswith(" "):
        entryname = tokens[3]
        subtok = tokens[4]
    else:
        subtok = tokens[3]
      
    tokens = subtok.split()
    ogs = ""
    gn = ""
    pe = ""
    sv = ""
    
    """Look for organism name"""
    foundos = False
    for t in tokens:
        if t.startswith("OS="):
            foundos = True
            ogs += re.sub("OS=", "", t)
        elif t.__contains__("="):
            break
        elif foundos:
            ogs += t
    
    foundgn = False
    for t in tokens:
        if t.startswith("GN="):
            foundgn = True
            gn += re.sub("GN=", "", t)
        elif t.__contains__("="):
            break
        elif foundgn:
            gn += t   
            
    foundpe = False
    for t in tokens:
        if t.startswith("PE="):
            foundpe = True
            pe += re.sub("PE=", "", t)
        elif t.__contains__("="):
            break
        elif foundpe:
            pe += t    
            
    foundsv = False
    for t in tokens:
        if t.startswith("SV="):
            foundsv = True
            sv += re.sub("SV=", "", t)
        elif t.__contains__("="):
            break
        elif foundsv:
            sv += t
            
    if gn != "":
        """Sometimes it's written like [GN=...], so let's discard the brackets"""
        gn = re.sub("\[", "", gn)
        gn = re.sub("\]", "", gn)
    
    if gn == "":
        """We didn't find GN=, so let's look for brackets"""
        subsubtok = subtok.split("[")
        if subsubtok.__len__() > 0:
            possible_gn = subsubtok[1].split("]")[0]
            if possible_gn != "":
                gn = possible_gn
    
    return (db, uniqueid, entryname, ogs, gn, pe, sv)

def import_ancestral_library(job):
    alib = phylobotmodels.AncestralLibrary.objects.get_or_create(shortname=job.settings.name)[0]
    #print "384:", alib
    
    relationship = phylobotmodels.AncestralLibrarySourceJob.objects.get_or_create(jobid=job.id, libid=alib.id)[0]
    #print "383:", relationship
    relationship.save()
    
    save_to_path = settings.MEDIA_ROOT + "/anclibs/asr_" + job.id.__str__() + ".db"
    #print "392:", save_to_path
    get_asrdb(job.id, save_to_path)
    
    if False == os.path.exists(save_to_path):
        print "398 - the db save didn't work"
    else:
        print "400 - the db save worked!"
        checkpoint = 9.0
        set_aws_checkpoint(job.id, checkpoint)
    
    alib.dbpath = "anclibs/asr_" + job.id.__str__() + ".db"
    alib.save()