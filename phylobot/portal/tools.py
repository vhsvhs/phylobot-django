import re, os
from portal.models import *

def scan_seq(seqpath):
    """Returns (file format, seq. type)"""
    format = None
    type = "aa"
    fin = open(seqpath, "r")
    firstline = fin.readline()
    secondline = fin.readline()
    fin.close()
    if firstline.split()[1].isalpha():
        format = "phylip"
    if firstline.startswith(">"):
        format = "fasta"
    
    return (format, type)

def get_taxa(seqpath, format, strip_indels = True):
    """Given the path to a sequence collection, this method returns a hashtable
    where key = sequence name, value = the sequence
    
    This method performs some QC on the sequences, and removes bad or illegal
    characters from taxon names."""
    taxa_seq = {}
    error_msgs = []
    fin = open(seqpath, "r")
    if format == "fasta":
        currseq = ""
        currtaxa = None
        
        """First, split lines ending in \r"""
        cleanlines = []
        for l in fin.xreadlines():
            for lt in l.split("\r"):
                cleanlines.append(lt)
        
        for l in cleanlines:
            if l.startswith(">"):
                this_taxa = re.sub( ">", "", l.strip() )
                if currtaxa != None:
                    taxa_seq[currtaxa] = currseq
                    currseq = ""
                currtaxa = this_taxa
                if currtaxa[0].isdigit():
                    # PAML complains if taxon start with numbers,
                    # so append "t" to the front of the taxon name
                    currtaxa = "t" + currtaxa
            else:
                l = re.sub(" ", "", l)
                l = re.sub("\?", "", l)
                l = re.sub("\_", "", l)
                l = re.sub("\.", "", l)
                if strip_indels:
                    l = re.sub("\-", "", l)
                currseq += l.strip()
        """Is this sequence name repeated?"""
        if currtaxa in taxa_seq:
            error_msgs.append("The sequence named " + currtaxa + " appears twice.") 
        
        taxa_seq[currtaxa] = currseq
    
    elif format == "phylip":
        for l in fin.xreadlines():
            if l.__len__() > 8:
                tokens = l.split()
                this_taxa = tokens[0]
                seq = tokens[1].strip()
                taxa_seq[this_taxa] = seq
    fin.close()
    return (taxa_seq, error_msgs)

def get_library_savetopath(jobid):
    dbpath = settings.MEDIA_ROOT + "/anclibs/asr_" + jobid.__str__() + ".db"
    return dbpath

def get_library_dbpath(alib):
    dbpath = alib.dbpath.__str__()
    dbpath = settings.MEDIA_ROOT + "/" + dbpath
    return dbpath

def check_ancestral_library_filepermissions(job=None, alib=None):
    """Ensure the ancestral database is writeable."""
    if job != None:
        save_to_path = get_library_savetopath(job.id)
    elif alib != None:
        save_to_path = get_library_dbpath(alib)
    elif job == None and alib == None:
        return False
    print "save_to_path:", save_to_path
    if os.path.exists(save_to_path):
        os.chmod(save_to_path, 0777)
        return True
    return False
        
        