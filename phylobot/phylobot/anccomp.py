"""This file contains methods that are used to compare ancestors."""

def d(ancx, ancy, method="Df"):
    """Compares a single site in ancestor x to a single site in ancestor Y.
    ancx and ancy are hashtables, with key = amino acid, value = probability of that a.a.
    """    

    # First, fix the PP vector to contain no zeros.
    if "-" in ancx.keys() or "X" in ancx.keys():
        return 0.0
    if "-" in ancy.keys() or "X" in ancy.keys():
        return 0.0
            
    pieces = []        
    if method == "Df": # i.e., k times p
        # observed/expectation:
        pieces.append( PDIST_WEIGHT*pdist(ancx, ancy) )
        # KL distance:
        pieces.append( KDIST_WEIGHT*kdist(ancx, ancy) )

    elif method == "k":
        # KL distance only:
        pieces.append( kdist(ancx, ancy) )
    elif method == "p":
        # observed/expectation only:
        pieces.append( pdist(ancx, ancy) )

    score = pieces[0]
    for piece in pieces[1:]:
        score *= piece
        
    score *= e_scale(ancx, ancy)
    return score

def kl_divergence(ppx, ppy):
    """Calculates the one-way Kullback-Leibler divergence between ppx and ppy"""

    # this first part is classic KL...
    ret = TINY    
    
    yvals = ppx
    xvals = ppy

    
    for a in AA_ALPHABET:
        #if ppy[a] > 0.01 and ppx[a] > 0.01:            
        ret += (xvals[a] * math.log(xvals[a]/yvals[a]))
    return ret

def kdist(ppx, ppy):
    if "-" in ppx.keys() and "-" in ppy.keys(): # indel to indel. . .
        return 0.0

    klxy = kl_divergence(ppx, ppy)
    klyx = kl_divergence(ppy, ppx)
    klsum = klxy + klyx
    return klsum 

def pdist(ppx, ppy):
    m = ap.params["model"]
    expected_p = 0.0
    observed_p = 0.0
    if "-" in ppx.keys() and "-" in ppy.keys(): # indel to indel. . .
        return 0.0
    pval = 0.0
    for a in AA_ALPHABET:
        for b in AA_ALPHABET:
            if a != b:
                #observed_p += ppx[a] * ppy[b]
                #expected_p += ppx[a] * math.exp( m[a][b] )# * 0.01 ) # to-do: times branch length?
                ep = ppx[a] * math.exp( m[a][b] )# * 0.01 ) # to-do: times branch length?
                op = ppx[a] * ppy[b]
                pval += abs( ep - op )**2
                #pval += op / ep
                #print "849", a, b, ppx[a], ppy[b], (ppx[a] * ppy[b]), (ppx[a] * math.exp( m[a][b] ))
    #pval = observed_p / expected_p
    return pval

def entropy(ppx):
    print "Entropy", ppx
    ret = 0.0
    for i in AA_ALPHABET:
        if ppx[a] > 0:
            ret += (ppx[a] * math.log(ppx[a]))
    return ret

def e_scale(ppx, ppy):
    enty = entropy(ppy)
    entx = entropy(ppx)
    e_dir = 1
    if (entx < enty) and ppy[ getmlstate(ppy) ] < CERTAINTY_CUTOFF and (enty - entx) > ENT_CUTOFF:
        e_dir *= -1
    return e_dir