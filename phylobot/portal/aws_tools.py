import boto
import boto.ec2
import boto.s3
import sys, time


ZONE = "us-west-1"

def push_jobfile_to_s3(jobid, filepath):
    """Pushes the startup files for a job to S3.
        jobid is the ID of the Job object,
        filepath is the path on this server to the file."""
    #s3 = S3Connection()
    
    s3 = boto.connect_s3()
    print "16:", s3.aws_access_key_id
    
    bucket = s3.lookup('phylobot.jobfiles')  # bucket names must be unique                                                                     
    if bucket == None:
        bucket = s3.create_bucket('phylbot.jobfiles')
    #bucket = s3.lookup('phylobot.jobfiles') 
    filename_short = filepath.split("/")[  filepath.split("/").__len__()-1 ]
    keyname = jobid.__str__() + "/" + filename_short
    k = bucket.new_key(keyname)
    k.set_contents_from_filename(filepath)
    k.make_public()
    
def get_jobfile_from_s3(jobid, filepath):
    s3 = boto.connect_s3()
    bucket = s3.get_bucket("phylobot-jobfiles")
    filename_short = filepath.split("/")[  filepath.split("/").__len__()-1 ]
    key = jobid.__str__() + "/" + filename_short
    for l in bucket.list( jobid.__str__() + "/"):
        if l.__contains__(filepath):
            get_contents_to_file(filename_short)




        