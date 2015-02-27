"""
populate.py generates random fake data in the database.
This is useful for testing.
"""
import os, random, sys, string

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def name_generator():
    names = ["Beagle", "Darwin", "McGee", "Starlight", "Cyan", "Tomato Sauce", "Tuesday", "Snotface"]
    return random.choice( names )

def populate_known():    
    print "\n. OK, I'm populating PhyloBot with default settings."
    print "\n. Use the /admin URL, on a running instance of this Django application, to access the database and change the default settings.\n"    
    
    build_software_paths()
    
    # We have only one queue, for now.
    jq = JobQueue.objects.get_or_create(id=1)[0]
    jq.save()
    
    add_jobstatus(-1, "draft", "Draft")
    add_jobstatus(0, "done", "Complete")
    add_jobstatus(1, "stopped", "Stopped")
    add_jobstatus(2, "stopping", "Waiting to Stop")
    add_jobstatus(4, "running", "Running")
    add_jobstatus(5, "queued", "Waiting in the Queue")
    add_jobstatus(6, "error", "Stalled, Error")
    
    add_aa("muscle", "muscle")
    add_aa("msaprobs", "msaprobs")

    add_rm("PROTCATLG")
    add_rm("PROTCATWAG")
    add_rm("PROTCATJTT")
    add_rm("PROTGAMMALG")
    add_rm("PROTGAMMAWAG")
    add_rm("PROTGAMMAJTT")
    
    add_seqfileformat(1,"fasta")
    add_seqfileformat(2,"phylip")
    
    add_seqtype(1, "amino acids", "aa")
    add_seqtype(2, "nucleotides", "nt")

def build_software_paths():
    print "49:", SoftwarePaths
    sp = SoftwarePaths.objects.get_or_create(softwarename="asrpipeline", path="python /Users/victor/Documents/SourceCode/asrpipeline/runme.py")
    print "51:", sp
    sp = sp[0]
    print "53:", sp
    sp.save()
    sp = SoftwarePaths.objects.get_or_create(softwarename="phyml", path="phyml")[0]
    sp.save()
    sp = SoftwarePaths.objects.get_or_create(softwarename="raxml", path="raxml")[0]
    sp.save()
    sp = SoftwarePaths.objects.get_or_create(softwarename="lazarus", path="python /common/lazarus/lazarus.py")[0]
    sp.save()   
    sp = SoftwarePaths.objects.get_or_create(softwarename="markov_models", path="/common/lazarus/paml/dat/")[0]
    sp.save()
    sp = SoftwarePaths.objects.get_or_create(softwarename="msaprobs", path="msaprobs")[0]
    sp.save()
    sp = SoftwarePaths.objects.get_or_create(softwarename="muscle", path="muscle")[0]
    sp.save()
    sp = SoftwarePaths.objects.get_or_create(softwarename="anccomp", path="python ~/Documents/SourceCode/anccomp/compare_ancs.py")[0]
    sp.save()

def add_aa(name, exe):
    aa = AlignmentAlgorithm.objects.get_or_create(name=name, executable=exe)[0]
    aa.save()

def add_seqtype(id, type, short):
    st = SeqType.objects.get_or_create(id=id, type=type, short=short)[0]
    st.save()

def add_rm(name):
    rm = RaxmlModel.objects.get_or_create(name=name)[0]
    rm.save()

def add_jobstatus(id,short,long):
    s = JobStatus.objects.get_or_create(id=id,short=short,long=long)[0]
    s.save()

def add_seqfileformat(id,name):
    ff = SeqFileFormat(id=id,name=name)
    ff.save()

def populate_examples():
    for ii in range(0, 50):
        id = id_generator()
        firstname = name_generator()
        lastname = name_generator()
        email = firstname + "@mail.com"
        pw = make_password("password")
        add_user( id.__str__(),lastname,firstname,email, pw )

    #for u in User.objects.all():
    #    this_profile = UserProfile.objects.get(user=u)
    #    print u.username, u.password, this_profile.user

    stopped_status = JobStatus.objects.get_or_create(id=1)[0]
    
    for u in User.objects.all():
        njobs = random.randint(0,10)
        for ii in range(0, njobs):
            job = add_job(u,stopped_status)

    # Print out what we have added to the user.
    #for c in Category.objects.all():
    #    for p in Page.objects.filter(category=c):
    #        print "- {0} - {1}".format(str(c), str(p))

def add_user(name,last,first,mail,pw):
    u = User.objects.get_or_create(username=name,last_name=last,first_name=first,email=mail,password=pw)[0]
    u.set_password(pw)
    u.save()
    up = UserProfile.objects.get_or_create(user=u)[0]
    up.save()

def add_job(owner, status):
    j = Job(owner=owner, status=status)
    j.save()

# Start execution here!
if __name__ == '__main__':
    #os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
    os.environ['DJANGO_SETTINGS_MODULE'] = 'phylobot.settings'
    
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    
    from django.db import models
    from django.contrib.auth.models import User
    from phylobot.models import *
    from portal.models import *
    from django.contrib.auth.hashers import *
    populate_known()
    #populate_examples()