from portal import aws_tools
from portal.aws_tools import *
import sqlite3 as lite
import time

SQLDBPATH = "job_daemon.db"
MAX_MSG_ATTEMPTS = 3

def print_splash():
    print "\n======================================="
    print "PhyloBot Job Daemon"
    print "written by Victor Hanson-Smith"
    print "victorhansonsmith@gmail.com" 
    print "======================================="

def build_db(dbpath):
    """Initializes all the tables. Returns the DB connection object.
    If tables already exist, they will NOT be overwritten."""
    con = lite.connect(dbpath)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS Instances(aws_id TEXT primary key unique, ip TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS PhyloBotJobs(jobid TEXT primary key unique)")
    cur.execute("CREATE TABLE IF NOT EXISTS JobInstance(jobid TEXT, aws_id TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS Log(message TEXT,code INT)")
    cur.execute("CREATE TABLE IF NOT EXISTS ErrorLog(message TEXT,code INT)")
    con.commit()
    return con

def add_instance(con, aws_id, ip):
    cur = con.cursor()
    sql = "insert or replace into Instances (aws_id, ip) values('" + aws_id.__str__() + "'"
    sql += ", '" + ip.__str__() + "')"
    cur.execute(sql)
    con.commit()

def remove_instance(con, aws_id):
    cur = con.cursor()
    sql = "delete from Instances where aws_id='" + aws_id.__str__() + "'"
    cur.execute(sql)
    sql = "delete from JobInstance where aws_id='" + aws_id.__str__() + "'"
    cur.execute(sql)
    con.commit()
    
def add_job(con, jobid):
    cur = con.cursor()
    sql = "insert or replace into PhyloBotJobs (jobid) values('" + jobid.__str__() + "')"
    cur.execute(sql)
    con.commit()
    
def remove_job(con, jobid):
    cur = con.cursor()
    sql = "delete from PhyloBotJobs where jobid='" + jobid.__str__() + "'"
    cur.execute(sql)
    sql = "delete from JobInstance where jobid='" + jobid.__str__() + "'"
    cur.execute(sql)
    con.commit()
    
def get_instances_for_job(con, jobid):
    cur = con.cursor()
    sql = "select aws_id from JobInstance where jobid='" + jobid.__str__() + "'"
    cur.execute(sql)
    x = cur.fetchall()
    ids = []
    for ii in x:
        ids.append( ii[0] )
    return ids    
    
def map_job_on_instance(con, jobid, aws_id):
    cur = con.cursor()
    sql = "insert or replace into JobInstance (jobid, aws_id)"
    sql += " values('" + jobid.__str__() + "', '" + aws_id.__str__() + "')"
    cur.execute(sql)
    con.commit()

def write_log(con, message, code=None):
    """
    Writes to the log file
    """
    cur = con.cursor()
    sql = "insert into Log (message"
    if code != None:
        sql += ",code"
    sql += ") values(\"" + message
    if code != None:
        sql += "\"," + code.__str__() + ")"
    else:
        sql += "\")"
    cur.execute(sql)
    con.commit()
    
    print "\n. " + message
    
def write_error(con, message, code=None):
    cur = con.cursor()
    sql = "insert into ErrorLog (message"
    if code != None:
        sql += ",code"
    sql += ") values(\"" + message
    if code != None:
        sql += "\"," + code.__str__() + ")"
    else:
        sql += "\")"
    cur.execute(sql)
    con.commit()
    print "\n. ERROR: " + message


def start_job(jobid, dbconn):
    """dbconn is a connection to the job_daemon database."""
    
    """First, let's check if this jobid is already mapped to any known instances."""
    known_instances = get_instances_for_job(dbconn, jobid)
    if known_instances.__len__() > 0:
        print "\n. It appears that jobid " + jobid.__str__() + " is already mapped to instance(s): " + known_instances.__str__()
        return known_instances[0]
    
    """Instantiate an AWS EC2 instance"""
    instance = None
    conn = boto.ec2.connect_to_region(ZONE)
    my_image = conn.get_image(image_id=AMI_SLAVE_MOTHER)
    reservation = conn.run_instances(image_id=AMI_SLAVE_MOTHER,
                                 key_name=INSTANCE_KEY_NAME,
                                 instance_type=INSTANCE_TYPE,
                                 security_groups=[INSTANCE_SECURITY_GROUP])
    instance = reservation.instances[0]
    
    try:
        write_log(dbconn, "Created the instance " + instance.id.__str__() )
        conn.create_tags( [instance.id], {"Name":"Instance built by PhyloBot Job Daemon from AMI " + AMI_SLAVE_MOTHER + " on " + time.ctime()} )
        
        """Wait for AWS to catchup"""
        time_count = 0
        print "\n. Waiting for AWS to catchup"
        while (instance.state != "running"):
            time_count += 3
            time.sleep(3)
            instance.update()
            if time_count > 120:
                print "\n. Error 25 - The instance hasn't reach 'running' state after too long. jobid=" + jobid.__str__()
                set_job_status(jobid, "Error activating cloud resources")
                return None
        
        write_log(dbconn, "OK. Instance " + instance.id + " is running at " + instance.ip_address , code=0)
        add_job(dbconn, jobid)
        add_instance(dbconn, instance.id, instance.ip_address)
        map_job_on_instance(dbconn, jobid, instance.id)
        set_job_status(jobid, "Starting, cloud resources activated")
        
        remote_command = "aws s3 cp s3://phylobot.jobfiles/" + jobid.__str__() + " ./"
        os.system("ssh -i ~/.ssh/phylobot-ec2-key.pem ubuntu@" + instance.ip_address + "'" + remote_command + "'")
        
        """Run the startup script"""
        
        """Run the job"""
        
        return instance.id
    except:
        e = sys.exc_info()[0]
        print "Error:"
        print e
        
        """An error occurred, so try to kill the instance."""
        write_log(dbconn, "There was a problem starting job " + jobid.__str__() + ". I'm terminating the instance " + instance.id__str__(), code=0)
        conn.terminate_instances( instance_ids=[instance.id] )
        return None


def stop_job(jobid, dbconn):
    """dbconn is a connection to the job_daemon database."""
    
    """Does this job exist on any known instances?"""
    known_instances = get_instances_for_job(dbconn, jobid)
    if known_instances.__len__() == 0:
        print "\n. It appears that jobid " + jobid.__str__() + " has not been mapped to any instances."
        set_job_status(jobid, "Stopped")
        remove_job(dbconn, jobid)
        return True
    else:
        """Stop each of the known AWS EC2 instances. If the execution state has been saved,
            then it can be recovered from S3, but otherwise the execution state is lost forever."""
        logmsg = "Terminating the following instances for jobid=" + jobid.__str__() + ":" + known_instances.__str__()
        print "\n. " + logmsg
        write_log(dbconn, logmsg, code=0)
        conn = boto.ec2.connect_to_region(ZONE)   
        conn.terminate_instances(instance_ids=known_instances)
        
        """Wait for AWS to catchup"""
        time_count = 0
        print "\n. Waiting for AWS to catchup"
        while(known_instances.__len__() > 0):
            """While our list of instances known to be assocated with this jobid
                contains at least one non-terminated instance, then keep waiting for
                AWS to terminate."""
            all_instances = conn.get_all_instances()
            alive_instanceids = []
            for reservation in all_instances:
                ai = reservation.instances[0]
                if ai.state != "terminated":
                    """If the instance isn't terminated, then it's on our list."""
                    alive_instanceids.append( ai.id )
            print "158:", alive_instanceids, all_instances
            
            
            for instanceid in known_instances:
                if instanceid not in alive_instanceids:
                    print "\n. 161 - instance " + instanceid.__str__() + " is terminated."
                    known_instances.remove( instanceid )
                    remove_instance(dbconn, instanceid )
            
            if known_instances.__len__() == 0:
                set_job_status(jobid, "Stopped.")
                remove_job(dbconn, jobid)
                return True
            
            if time_count > 120:
                write_error(dbconn, "\n. Error 25 - The instance hasn't reach 'terminated' state after too long. jobid=" + jobid.__str__() )
                set_job_status(jobid, "Error evaporating clouds resources")
                return False
        
            time_count += 3
            time.sleep(3)
    
    return True

"""
    This is the main loop for the daemon
"""
print_splash()
dbconn = build_db(SQLDBPATH)
write_log(dbconn, "Connected to the daemon DB at " + SQLDBPATH.__str__())
write_log(dbconn, "The PhyloBot job daemon is launching. . .")
while(True):    
    conn = boto.sqs.connect_to_region(ZONE)
    queue = conn.get_queue("phylobot-jobs")
    if queue == None:
        queue = conn.create_queue("phylobot-jobs")
    
    """Get any messages on the SQS queue"""
    messages = queue.get_messages()
    if messages.__len__() > 0:
        print "\n. Daemon Status: There are ", messages.__len__().__str__(), "pending messages in the SQS queue."
    for msg in messages:
        body = msg.get_body()
                
        """
            Parse the Message
        """
        tokens = body.split()
        if tokens.__len__() < 2:
            """This is an invalid queue message."""
            print "\n. Error 39 - job_daemon - A message appears invalid, deleting it:"
            print body
            queue.delete_message( msg )
            """We're done. Skip to the next msg"""
            continue
        
        msg_action = tokens[0]
        msg_jobid = tokens[1]
        msg_attempts = 0
        if tokens.__len__() > 2:
            msg_attempts = int( tokens[2] )
        
        print "\n. SQS:", body
        
        """If the msg has been attempted too many times, delete it, skip to next."""
        if msg_attempts > MAX_MSG_ATTEMPTS:
            print "\n. This message reached the maximum number of attempts without success, delete it."
            print body
            queue.delete_message( msg )
            continue
    
        """
            Message Dispatch
        """
        if msg_action == "start":
            aws_id = start_job(msg_jobid, dbconn)
            
            """Did the 'start' action fail?"""
            if aws_id == None:
                """Here we delete the msg from the queue, increment the attempts counter,
                    then add the message back onto the queue."""
                queue.delete_message( msg )
                """Re-queue the msg with attempts += 1"""
                sqs_start(msg_jobid, attempts=msg_attempts+1 )
                continue
            else:
                queue.delete_message( msg )
                continue
  
        elif msg_action == "stop":
            flag = stop_job(msg_jobid, dbconn)
            queue.delete_message( msg )
            if flag == False:
                """It didn't successfully stop, so let's try again later"""
                sqs_stop(jobid, attempts=msg_attempts+1 )
            continue

    # outside the for loop, but inside the while loop:
    time.sleep(5)
