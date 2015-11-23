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

def get_taxa(seqpath, format):
    """Given the path to a sequence collection, this method returns a hashtable
    where key = sequence name, value = the sequence"""
    taxa_seq = {}
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
            else:
                l = re.sub(" ", "", l)
                l = re.sub("\?", "", l)
                currseq += l.strip()
        taxa_seq[currtaxa] = currseq
    
    elif format == "phylip":
        for l in fin.xreadlines():
            if l.__len__() > 15:
                tokens = l.split()
                this_taxa = tokens[0]
                seq = tokens[1].strip()
                taxa_seq[this_taxa] = seq
    fin.close()
    return taxa_seq

def get_library_savetopath(jobid):
    return settings.MEDIA_ROOT + "/anclibs/asr_" + jobid.__str__() + ".db"

def check_ancestral_library_filepermissions(jobid):
    """Ensure the ancestral database is writeable."""
    save_to_path = get_library_savetopath(jobid)
    if os.file.exists(save_to_path):
        os.system(save_to_path, 0777)
        return True
    return False
        
        