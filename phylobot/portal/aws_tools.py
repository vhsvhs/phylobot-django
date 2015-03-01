import boto
import boto.ec2
import boto.s3
from boto.s3.connection import S3Connection
import boto.sqs
from boto.sqs.message import Message
import sys, time

ZONE = "us-west-1"
AMI_SLAVE_MOTHER = "ami-6b23c62f"
INSTANCE_TYPE = "t2.micro"
INSTANCE_KEY_NAME = "phylobot-ec2-key"
INSTANCE_SECURITY_GROUP = 'phylobot-security'

def push_jobfile_to_s3(jobid, filepath):
    """Pushes the startup files for a job to S3.
        jobid is the ID of the Job object,
        filepath is the path on this server to the file."""
    #s3 = S3Connection()
    
    s3 = boto.connect_s3()
    print "16:", s3.aws_access_key_id
    
    bucket = s3.lookup('phylobot.jobfiles')  # bucket names must be unique                                                                     
    if bucket == None:
        bucket = s3.create_bucket('phylobot.jobfiles')
    #bucket = s3.lookup('phylobot.jobfiles') 
    filename_short = filepath.split("/")[  filepath.split("/").__len__()-1 ]
    keyname = jobid.__str__() + "/" + filename_short
    k = bucket.new_key(keyname)
    k.set_contents_from_filename(filepath)
    k.make_public()
    
def get_jobfile_from_s3(jobid, filepath):
    s3 = boto.connect_s3()
    bucket = s3.get_bucket("phylobot.jobfiles")
    filename_short = filepath.split("/")[  filepath.split("/").__len__()-1 ]
    key = jobid.__str__() + "/" + filename_short
    for l in bucket.list( jobid.__str__() + "/"):
        if l.__contains__(filepath):
            get_contents_to_file(filename_short)
            
def get_job_status(jobid):
    """Returns the value of the status key for the job"""
    s3 = boto.connect_s3()
    bucket = s3.get_bucket("phylobot.jobfiles")
    
    STATUS_KEY = jobid.__str__() + "/status"
    key = bucket.get_key(STATUS_KEY)
    if key == None:
        return "Waiting to Launch"   
    else:
        return key.get_contents_as_string()    


def set_job_status(jobid, message):
    s3 = boto.connect_s3()
    bucket = s3.get_bucket("phylobot.jobfiles")
    if bucket == None:
        s3.create_bucket("phylobot.jobfiles")
        bucket = s3.get_bucket("phylobot.jobfiles")

    STATUS_KEY = jobid.__str__() + "/status"
    key = bucket.get_key(STATUS_KEY)
    if key == None:
        key = bucket.new_key(STATUS_KEY) 
    key.set_contents_from_string(message) 


def set_job_exe(jobid, exe):
    s3 = S3Connection()
    
    bucket = s3.lookup("phylobot.jobfiles")
    if bucket == None:
        s3.create_bucket(S3_BUCKET)
        bucket = s3.get_bucket(S3_BUCKET)    
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
       