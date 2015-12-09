from daemon import *

from phylobot import settings

BACKUPDAEMON_SLEEP = 3600 # seconds
S3_BACKUPBUCKET = get_env_variable("S3_BACKUPBUCKET")

def print_splash():
    print "\n======================================="
    print "PhyloBot Backup Daemon"
    print "written by Victor Hanson-Smith"
    print "victorhansonsmith@gmail.com" 
    print ""
    print "Current AWS Settings:"
    print ". ZONE: ", ZONE
    print ". S3LOCATION:", S3LOCATION
    print ". S3BUCKET:", S3BUCKET
    print ". S3_BACKUPBUCKET:", S3_BACKUPBUCKET
    print ". SQS_JOBQUEUE_NAME:", SQS_JOBQUEUE_NAME
    print ". AMI_SLAVE_MOTHER:", AMI_SLAVE_MOTHER
    print "========================================="

""" Main Daemon Loop """    
while(True):    
    
    """Get the S3 bucket for backup data"""
    s3 = boto.connect_s3()    
    bucket = s3.lookup(S3_BACKUPBUCKET)  # bucket names must be unique                                                                     
    if bucket == None:
        bucket = s3.create_bucket(S3_BACKUPBUCKET, location=S3LOCATION)
        bucket.set_acl('private')
    
    """Backup the Job Daemon database."""
    jobdaemon_backup_key = "jobdaemon.db"
    key = bucket.get_key(jobdaemon_backup_key)
    if key == None:
        key = bucket.new_key(jobdaemon_backup_key) 
    key.set_contents_from_filename(DAEMONDBPATH) 
    
    """Backup the main PhyloBot project."""
    phylobot_dbpath = settings.DATABASES['default']['NAME']
    phylobot_db_backup_key = "phylobot.db"
    key = bucket.get_key(phylobot_db_backup_key)
    if key == None:
        key = bucket.new_key(phylobot_db_backup_key) 
    key.set_contents_from_filename(phylobot_dbpath)     
    
    """Sleep for a while until we do the next backup"""
    time.sleep( BACKUPDAEMON_SLEEP )