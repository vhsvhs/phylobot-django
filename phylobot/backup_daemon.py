from daemon import *

from phylobot import settings

BACKUPDAEMON_SLEEP = 3600 # 1 hour, in seconds
S3_BACKUPBUCKET = get_env_variable("S3_BACKUPBUCKET")

PHYLOBOT_REPO = get_env_variable("PHYLOBOT_REPO")
phylobot_dbpath = settings.DATABASES['default']['NAME']
jobdaemon_dbpath = PHYLOBOT_REPO + "/phylobot/" + DAEMONDBPATH

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
    print ". phylobot_dbpath:", phylobot_dbpath
    print ". DAEMONDBPATH:", jobdaemon_dbpath
    print "========================================="

print_splash()


""" Main Daemon Loop """    
while(True):    
    JOBDAEMONDB_BACKUP_KEY = "jobdaemon.db"
    PHYLOBOTDB_BACKUP_KEY = "phylobot.db"

    """Get the S3 bucket for backup data"""
    s3 = boto.connect_s3()    
    bucket = s3.lookup(S3_BACKUPBUCKET)  # bucket names must be unique                                                                     
    if bucket == None:
        bucket = s3.create_bucket(S3_BACKUPBUCKET, location=S3LOCATION)
        bucket.set_acl('private')
    
    """Get the sizes of the last backup -- we'll use this information
        to ensure we're always updating with a newer (i.e. bigger)
        database object. If the current database is significantly smaller
        than the backed-up DB, then this indicates that perhaps our
        current copy of the DB is corrupted, and should not be backed-up."""
    jobdaemondb_backup_lastsize = None
    phylobotdb_backup_lastsize = None
    for key in bucket.list():
        if key.name == JOBDAEMONDB_BACKUP_KEY:
            jobdaemondb_backup_lastsize = key.size
        elif key.name == PHYLOBOTDB_BACKUP_KEY:
            phylobotdb_backup_lastsize = key.size
    
    """Compare sizes"""
    jobdaemondb_backup_currsize = os.path.getsize(jobdaemon_dbpath)
    if jobdaemondb_backup_currsize != None and jobdaemondb_backup_lastsize != None:
        if jobdaemondb_backup_currsize < 0.8 * jobdaemondb_backup_lastsize:
            print "\n. Hmmm... the Job Daemon DB looks small compared to the last backup."
            JOBDAEMONDB_BACKUP_KEY = "jobdaemon.db" + time.time()
            print "\. I'm backing up the Job Daemon at a new key:", JOBDAEMONDB_BACKUP_KEY

    phylobotdb_backup_currsize = os.path.getsize(phylobot_dbpath)
    if phylobotdb_backup_currsize != None and phylobotdb_backup_lastsize != None:
        if phylobotdb_backup_currsize < 0.8 * phylobotdb_backup_lastsize:
            print "\n. Hmmm... the PhyloBot DB looks small compared to the last backup."
            PHYLOBOTDB_BACKUP_KEY = "phylobot.db" + time.time()
            print "\. I'm backing up the PhyloBot DB at a new key:", PHYLOBOTDB_BACKUP_KEY    
    
    """Backup the Job Daemon database (i.e. the job queue)."""    
    key = bucket.get_key(JOBDAEMONDB_BACKUP_KEY)
    if key == None:
        key = bucket.new_key(JOBDAEMONDB_BACKUP_KEY) 
    key.set_contents_from_filename(jobdaemon_dbpath) 
    
    """Backup the main PhyloBot project."""
    key = bucket.get_key(PHYLOBOTDB_BACKUP_KEY)
    if key == None:
        key = bucket.new_key(PHYLOBOTDB_BACKUP_KEY) 
    key.set_contents_from_filename(phylobot_dbpath)     
    
    """Sleep for a while until we do the next backup"""
    time.sleep( BACKUPDAEMON_SLEEP )