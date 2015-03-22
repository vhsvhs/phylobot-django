from portal.view_tools import *

def faq_fasta(request):
    return render_to_response('faq_fasta.html')

def faq_newick(request):
    return render_to_response('faq_newick.html')