import boto
import boto.ec2
import boto.s3
from boto.s3.connection import S3Connection
from boto.s3.connection import Location
import boto.sqs
from boto.sqs.message import Message
import sys, time

from os import listdir, environ
from django.core.exceptions import ImproperlyConfigured
def get_env_variable(var_name):
    """Get the env. variable, or return exception"""
    try:
        return environ[var_name]
    except KeyError:
        import getpass
        curr_username = getpass.getuser()
        error_msg = "Set the {} environment variable for user {}".format(var_name, curr_username)
        raise ImproperlyConfigured(error_msg)

ZONE = get_env_variable("AWSZONE") #"us-west-1"
#AMI_SLAVE_MOTHER = "ami-6fb3552b" # march 13, 2015
AMI_SLAVE_MOTHER = get_env_variable("EC2_COMPUTE_INSTANCE_AMI_MOTHER") #"ami-59db3a1d" # march 23, 2015
INSTANCE_KEY_NAME = get_env_variable("EC2_COMPUTE_INSTANCE_KEYNAME")# "phylobot-ec2-key"
INSTANCE_SECURITY_GROUP = get_env_variable("EC2_INSTANCE_SECURITY_GROUP_NAME") #'phylobot-security'

S3LOCATION = Location.USWest
S3BUCKET = get_env_variable("S3BUCKET")
SQS_JOBQUEUE_NAME = get_env_variable("SQS_JOBQUEUE_NAME")

def get_instance_type(jobid):
    """Determine what size of instance is appropriate, based on the nsites and seqlen
        of the job."""
    ntaxa = int( get_ntaxa(jobid) )
    nsites = int( get_seqlen(jobid) )
        
    if ntaxa == None or nsites == None:
        return "t2.small"
    
    """To-do: these thresholds need to be tuned, based on performance tests."""
    if ntaxa < 40 and nsites < 300:
        return "t2.small"
    elif ntaxa < 60 and nsites < 700:
        return "t2.medium"
    elif ntaxa < 100 and nsites < 1000:
        return "c4.large"
    else:
        return "r3.large"

def get_s3_bucket():
    s3 = boto.connect_s3()    
    bucket = s3.lookup(S3BUCKET)  # bucket names must be unique                                                                     
    if bucket == None:
        bucket = s3.create_bucket(S3BUCKET, location=S3LOCATION)
        bucket.set_acl('public-read')
    return bucket

def get_sqs_queue():
    conn = boto.sqs.connect_to_region(ZONE)
    queue = conn.get_queue(SQS_JOBQUEUE_NAME)
    if queue == None:
        queue = conn.create_queue(SQS_JOBQUEUE_NAME)
    return queue

def clear_all_s3(jobid):
    bucket = get_s3_bucket()
    keys = bucket.list( prefix=jobid.__str__() )
    for k in keys:
        print "deleting key - ", k
        bucket.delete_key( k )  

def push_jobfile_to_s3(jobid, filepath, new_filepath = None):
    """Pushes the startup files for a job to S3.
        jobid is the ID of the Job object,
        filepath is the path on this server to the file."""
    bucket = get_s3_bucket()
    filename_short = filepath.split("/")[  filepath.split("/").__len__()-1 ]
    keyname = jobid.__str__() + "/" + filename_short
    k = bucket.new_key(keyname)
    
    if new_filepath == None:
        new_filepath = filepath
    k.set_contents_from_filename(new_filepath)
    k.set_acl('public-read')
    k.make_public()
    
def get_asrdb(jobid, save_to_path):
    print "88: entered get_asrdb"
    bucket = get_s3_bucket()
    DBKEY = jobid.__str__() + "/sqldb"
    print DBKEY
    key = bucket.get_key(DBKEY)
    print "46 get_asrdb:", key, save_to_path
    if key == None:
        return None
    key.get_contents_to_filename(save_to_path)

            
def get_job_status(jobid):    
    """Returns the value of the status key for the job"""
    bucket = get_s3_bucket()
    STATUS_KEY = jobid.__str__() + "/status"
    key = bucket.get_key(STATUS_KEY)
    if key == None:
        set_job_status(jobid, "Stopped")
        return "Stopped"   
    else:
        return key.get_contents_as_string()    

def set_job_status(jobid, message):
    bucket = get_s3_bucket()
    STATUS_KEY = jobid.__str__() + "/status"
    key = bucket.get_key(STATUS_KEY)
    if key == None:
        key = bucket.new_key(STATUS_KEY) 
    key.set_contents_from_string(message)
    key.set_acl('public-read')

def set_aws_checkpoint(jobid, checkpoint):
    bucket = get_s3_bucket()
    CHECKPOINT_KEY = jobid.__str__() + "/checkpoint"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        key = bucket.new_key(CHECKPOINT_KEY) 
    key.set_contents_from_string(checkpoint.__str__()) 
    key.set_acl('public-read')

def get_aws_checkpoint(jobid):
    start = time.time()
    bucket = get_s3_bucket()
    #print "131:", time.time() - start
    CHECKPOINT_KEY = jobid.__str__() + "/checkpoint"
    key = bucket.get_key(CHECKPOINT_KEY)
    stop = time.time()
    #print "134:", jobid, stop-start
    if key == None:
        set_aws_checkpoint(jobid, 0)
        return 0
    return key.get_contents_as_string() 

def set_ntaxa(jobid, ntaxa):
    bucket = get_s3_bucket()
    CHECKPOINT_KEY = jobid.__str__() + "/ntaxa"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        key = bucket.new_key(CHECKPOINT_KEY) 
    key.set_contents_from_string(ntaxa.__str__()) 
    key.set_acl('public-read')
    
def get_ntaxa(jobid):
    bucket = get_s3_bucket()
    CHECKPOINT_KEY = jobid.__str__() + "/ntaxa"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        set_last_user_command(jobid, None)
        return None
    return key.get_contents_as_string() 

def set_seqlen(jobid, seqlen):
    bucket = get_s3_bucket()
    CHECKPOINT_KEY = jobid.__str__() + "/seqlen"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        key = bucket.new_key(CHECKPOINT_KEY) 
    key.set_contents_from_string(seqlen.__str__()) 
    key.set_acl('public-read')

def get_seqlen(jobid):
    bucket = get_s3_bucket()
    CHECKPOINT_KEY = jobid.__str__() + "/seqlen"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        set_last_user_command(jobid, None)
        return None
    return key.get_contents_as_string() 


def set_last_user_command(jobid, command):
    bucket = get_s3_bucket()
    CHECKPOINT_KEY = jobid.__str__() + "/last_user_command"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        key = bucket.new_key(CHECKPOINT_KEY) 
    key.set_contents_from_string(command.__str__()) 
    key.set_acl('public-read')

def get_last_user_command(jobid):
    bucket = get_s3_bucket()
    CHECKPOINT_KEY = jobid.__str__() + "/last_user_command"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        set_last_user_command(jobid, None)
        return None
    return key.get_contents_as_string() 

def set_job_exe(jobid, exe):
    bucket = get_s3_bucket()  
    EXE_KEY = jobid.__str__() + "/exe"
    print "attempting to get key", EXE_KEY
    key = bucket.get_key(EXE_KEY)
    if key == None:
        key = bucket.new_key(EXE_KEY)

        #key = bucket.get_key(STATUS_KEY) 
    if key == None:
        print "\n. Error 39 - the key is None"
        exit()   
    key.set_contents_from_string(exe)
    key.set_acl('public-read')

def get_job_exe(jobid):
    s3 = S3Connection()
    bucket = s3.lookup(S3BUCKET)
    if bucket == None:
        return None  
    EXE_KEY = jobid.__str__() + "/exe"
    print "attempting to get key", EXE_KEY
    key = bucket.get_key(EXE_KEY)
    if key == None:
        return None
 
    return key.get_contents_as_string(exe)

def sqs_start(jobid, attempts=0):
    queue = get_sqs_queue()
    m = Message()
    m.set_body('start ' + jobid.__str__() + " " + attempts.__str__())
    queue.write(m)
    
def sqs_stop(jobid, attempts=0):
    queue = get_sqs_queue()
    m = Message()
    m.set_body('stop ' + jobid.__str__() + " " + attempts.__str__())
    queue.write(m)   
    
def sqs_release(jobid, attempts=0):
    queue = get_sqs_queue()
    m = Message()
    m.set_body('release ' + jobid.__str__() + " " + attempts.__str__())
    queue.write(m)     
    
def setup_slave_startup_script(jobid): 
    s3 = S3Connection()
    bucket = s3.lookup(S3BUCKET)
    SLAVE_STARTUP_SCRIPT_KEY = jobid.__str__() + "/slave_startup_script"
    key = bucket.get_key(SLAVE_STARTUP_SCRIPT_KEY)
    if key == None:
        key = bucket.new_key(SLAVE_STARTUP_SCRIPT_KEY)
    if key == None:
        print "\n. Error 115 - the key is None"
        exit()   
        
    """The startup script:"""
    l = ""
    l += "cd ~/\n"
    l += "sudo rm -rf repository/asr-pipeline\n"
    l += "cd repository\n"
    l += "sudo git clone https://github.com/vhsvhs/asr-pipeline\n"
    l += "sudo rm -rf lazarus\n"
    l += "sudo git clone https://code.google.com/p/project-lazarus/ lazarus\n"
    l += "cd ~/\n"
    key.set_contents_from_string(l) 
    key.set_acl('public-read')    
       