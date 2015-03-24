import boto
import boto.ec2
import boto.s3
from boto.s3.connection import S3Connection
from boto.s3.connection import Location
import boto.sqs
from boto.sqs.message import Message
import sys, time

ZONE = "us-west-1"
#AMI_SLAVE_MOTHER = "ami-6fb3552b" # march 13, 2015
AMI_SLAVE_MOTHER = "ami-e1d938a5" # march 23, 2015
INSTANCE_TYPE = "t2.micro"
INSTANCE_KEY_NAME = "phylobot-ec2-key"
INSTANCE_SECURITY_GROUP = 'phylobot-security'
S3LOCATION = Location.USWest

def clear_all_s3(jobid):
    s3 = boto.connect_s3()
    print "16:", s3.aws_access_key_id
    
    bucket = s3.lookup('phylobot-jobfiles')  # bucket names must be unique                                                                     
    if bucket == None:
        bucket = s3.create_bucket('phylobot-jobfiles', location=S3LOCATION)
        bucket.set_acl('public-read')
        
    keys = bucket.list( prefix=jobid.__str__() )
    for k in keys:
        print "deleting key - ", k
        bucket.delete_key( k )  

def push_jobfile_to_s3(jobid, filepath, new_filepath = None):
    """Pushes the startup files for a job to S3.
        jobid is the ID of the Job object,
        filepath is the path on this server to the file."""
    #s3 = S3Connection()
    
    s3 = boto.connect_s3()
    print "16:", s3.aws_access_key_id
    
    bucket = s3.lookup('phylobot-jobfiles')  # bucket names must be unique                                                                     
    if bucket == None:
        bucket = s3.create_bucket('phylobot-jobfiles', location=S3LOCATION)
        bucket.set_acl('public-read')
    #bucket = s3.lookup('phylobot-jobfiles') 
    filename_short = filepath.split("/")[  filepath.split("/").__len__()-1 ]
    keyname = jobid.__str__() + "/" + filename_short
    k = bucket.new_key(keyname)
    
    if new_filepath == None:
        new_filepath = filepath
    k.set_contents_from_filename(new_filepath)
    k.set_acl('public-read')
    k.make_public()
    
def get_asrdb(jobid, save_to_path):
    s3 = boto.connect_s3()
    bucket = s3.lookup("phylobot-jobfiles")
    DBKEY = jobid.__str__() + "/sqldb"
    print DBKEY
    key = bucket.get_key(DBKEY)
    print "46:", key, save_to_path
    if key == None:
        return None
    key.get_contents_to_filename(save_to_path)
            
def get_job_status(jobid):    
    """Returns the value of the status key for the job"""
    s3 = boto.connect_s3()
    bucket = s3.lookup("phylobot-jobfiles")
    if bucket == None:
        bucket = s3.create_bucket("phylobot-jobfiles", location=S3LOCATION)
        bucket.set_acl('public-read')
    
    STATUS_KEY = jobid.__str__() + "/status"
    key = bucket.get_key(STATUS_KEY)
    if key == None:
        set_job_status(jobid, "Stopped")
        return "Stopped"   
    else:
        return key.get_contents_as_string()    

def set_job_status(jobid, message):
    s3 = boto.connect_s3()
    bucket = s3.lookup("phylobot-jobfiles")
    if bucket == None:
        bucket = s3.create_bucket("phylobot-jobfiles", location=S3LOCATION)
        bucket.set_acl('public-read')

    STATUS_KEY = jobid.__str__() + "/status"
    key = bucket.get_key(STATUS_KEY)
    if key == None:
        key = bucket.new_key(STATUS_KEY) 
    key.set_contents_from_string(message)
    key.set_acl('public-read')

def set_aws_checkpoint(jobid, checkpoint):
    s3 = boto.connect_s3()
    bucket = s3.lookup("phylobot-jobfiles")
    if bucket == None:
        bucket = s3.create_bucket("phylobot-jobfiles", location=S3LOCATION)
        bucket.set_acl('public-read')

    CHECKPOINT_KEY = jobid.__str__() + "/checkpoint"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        key = bucket.new_key(CHECKPOINT_KEY) 
    key.set_contents_from_string(checkpoint.__str__()) 
    key.set_acl('public-read')

def get_aws_checkpoint(jobid):

    s3 = boto.connect_s3()
    bucket = s3.lookup("phylobot-jobfiles")
    if bucket == None:
        bucket = s3.create_bucket("phylobot-jobfiles", location=S3LOCATION)
        bucket.set_acl('public-read')

    CHECKPOINT_KEY = jobid.__str__() + "/checkpoint"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        set_aws_checkpoint(jobid, 0)
        return 0
    return key.get_contents_as_string() 


def set_last_user_command(jobid, command):
    s3 = boto.connect_s3()
    bucket = s3.lookup("phylobot-jobfiles")
    if bucket == None:
        bucket = s3.create_bucket("phylobot-jobfiles", location=S3LOCATION)
        bucket.set_acl('public-read')

    CHECKPOINT_KEY = jobid.__str__() + "/last_user_command"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        key = bucket.new_key(CHECKPOINT_KEY) 
    key.set_contents_from_string(command.__str__()) 
    key.set_acl('public-read')

def get_last_user_command(jobid):
    s3 = boto.connect_s3()
    bucket = s3.lookup("phylobot-jobfiles")
    if bucket == None:
        bucket = s3.create_bucket("phylobot-jobfiles", location=S3LOCATION)
        bucket.set_acl('public-read')

    CHECKPOINT_KEY = jobid.__str__() + "/last_user_command"
    key = bucket.get_key(CHECKPOINT_KEY)
    if key == None:
        set_last_user_command(jobid, None)
        return None
    return key.get_contents_as_string() 




def set_job_exe(jobid, exe):
    s3 = S3Connection()
    
    bucket = s3.lookup("phylobot-jobfiles")
    if bucket == None:
        bucket = s3.create_bucket(S3_BUCKET, location=S3LOCATION)  
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
    
    bucket = s3.lookup("phylobot-jobfiles")
    if bucket == None:
        return None  
    EXE_KEY = jobid.__str__() + "/exe"
    print "attempting to get key", EXE_KEY
    key = bucket.get_key(EXE_KEY)
    if key == None:
        return None
 
    return key.get_contents_as_string(exe)

def sqs_start(jobid, attempts=0):
    conn = boto.sqs.connect_to_region(ZONE)
    queue = conn.get_queue("phylobot-jobs")
    if queue == None:
        queue = conn.create_queue("phylobot-jobs")
    
    m = Message()
    m.set_body('start ' + jobid.__str__() + " " + attempts.__str__())
    queue.write(m)
    
def sqs_stop(jobid, attempts=0):
    conn = boto.sqs.connect_to_region(ZONE)
    queue = conn.get_queue("phylobot-jobs")
    if queue == None:
        queue = conn.create_queue("phylobot-jobs")
    m = Message()
    m.set_body('stop ' + jobid.__str__() + " " + attempts.__str__())
    queue.write(m)   
    
def sqs_release(jobid, attempts=0):
    conn = boto.sqs.connect_to_region(ZONE)
    queue = conn.get_queue("phylobot-jobs")
    if queue == None:
        queue = conn.create_queue("phylobot-jobs")
    m = Message()
    m.set_body('release ' + jobid.__str__() + " " + attempts.__str__())
    queue.write(m)     
    
def setup_slave_startup_script(jobid): 
    s3 = S3Connection()
    bucket = s3.lookup("phylobot-jobfiles")
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
       