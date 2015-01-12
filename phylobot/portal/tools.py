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
    taxa_seq = {}
    fin = open(seqpath, "r")
    if format == "fasta":
        currseq = ""
        currtaxa = None
        for l in fin.xreadlines():
            if l.startswith(">"):
                this_taxa = re.sub( ">", "", l.strip() )
                if currtaxa != None:
                    taxa_seq[currtaxa] = currseq
                    currseq = ""
                currtaxa = this_taxa
            else:
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
        
        