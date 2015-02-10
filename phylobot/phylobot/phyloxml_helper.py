import os, re, sys, dendropy
import Bio
if float(Bio.__version__) < 1.63:
    print "\n\nPlease update your BioPython library."
    print "You are currently using version", Bio.__version__
    print "However, this ASR pipeline requires version 1.63 or newer."
    exit()
from Bio import Phylo # Note, this must be version 1.63 or newer.
from Bio.Phylo import PhyloXML
try:
    from StringIO import StringIO # Python 2
except ImportError:
    from io import StringIO # Python 3

def annotate_phyloxml(xmlstring, urlprefix):
    """Input a line of PhyloXML containing a cladogram with ancestral node numbers, outputs that line with additional markup (possibly) added.
    Specifically, changes <confidence> to <name>, add adds <annotations> with a clickable URL
    to the ancestral PP file.
    urlprefix example: 1/msaprobs.PROTCATLG/
    """
    
    #
    # continue here
    #
    
    xmlstring = re.sub("confidence", "name", xmlstring)
    xmlstring = re.sub("type=\"unknown\"", "", xmlstring)

    # The following line breaks jsphylosvg, for unknown reasons.
    # apparently, the whitespace is important in their javascript.
    #line = re.sub(" ", "", line)

    if xmlstring.__contains__("name"):
        name = xmlstring
        name = re.sub("\n", "", name)
        name = re.sub(" ", "", name)
        name = re.sub("<name>", "", name)
        name = re.sub("<\/name>", "", name)
        #print "22: name=", name
        if name.isdigit(): # this taxa name is all numbers, and therefore, an ancestor
            xmlstring += "<annotation>"
            xmlstring += "<desc>Ancestor #" + name + "</desc>"
            url = urlprefix + "/Node" + name
            xmlstring += "<uri>" + url + "</uri>"
            xmlstring += "<a>fake link</a>"
            xmlstring += "</annotation>"
    return xmlstring
