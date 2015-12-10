from daemon import *

MAX_MSG_ATTEMPTS = 3
MAX_WAIT = 240

def print_splash():
    print "\n======================================="
    print "PhyloBot Job Daemon"
    print "written by Victor Hanson-Smith"
    print "victorhansonsmith@gmail.com" 
    print ""
    print "Current AWS Settings:"
    print ". ZONE: ", ZONE
    print ". S3LOCATION:", S3LOCATION
    print ". S3BUCKET:", S3BUCKET
    print ". SQS_JOBQUEUE_NAME:", SQS_JOBQUEUE_NAME
    print ". AMI_SLAVE_MOTHER:", AMI_SLAVE_MOTHER
    print ". Max. wait for port 22:", MAX_WAIT, "seconds"
    print "========================================="

def build_db(dbpath):
    """Initializes all the tables. Returns the DB connection object.
    If tables already exist, they will NOT be overwritten."""
    try:
        con = lite.connect(dbpath)
        cur = con.cursor()
    except sqlite3.OperationalError:
        print "\n. Error, I couldn't open a connection with boto to AWS."
        print ". Try running this script as sudo."
        exit()
        
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
        return (True, known_instances[0])
    
        #
        # continue here -- check that the instance is OK.
        #
    
    INSTANCE_TYPE = get_instance_type(jobid)
    
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
        write_log(dbconn, "Created the instance " + instance.id.__str__() + ", instance type: " + INSTANCE_TYPE.__str__() )
        conn.create_tags( [instance.id], {"Name":"PhyloBot Job " + jobid.__str__() + " using AMI " + AMI_SLAVE_MOTHER + " on " + time.ctime()} )
        
        """Wait for AWS to catchup"""
        time_count = 0

        print "\n. Waiting for AWS to catchup"
        while (instance.state != "running"):
            time_count += 3
            time.sleep(3)
            instance.update()
            if time_count > MAX_WAIT:
                print "\n. Error 25 - The instance hasn't reach 'running' state after too long. jobid=" + jobid.__str__()
                set_job_status(jobid, "Error activating cloud resources: the instance failed to start.")
                return (False, None)
        
        print "\n. Waiting for port 22 to open on the instance"
        portopen = False
        set_job_status(jobid, "Waiting for the replicate to open a communication port.")
        time_count = 0
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while (portopen == False):
            try:
                s.connect((instance.ip_address, 22))
                """If we arrive here, then the port 22 is open"""
                portopen = True
            except socket.error:
                """It's not open yet"""
                time_count += 3
            if time_count > MAX_WAIT:
                print "\n. Error 168 - The instance hasn't opened its port 22 after " + MAX_WAIT.__str__() + " seconds. jobid=" + jobid.__str__()
                set_job_status(jobid, "Error activating cloud resources: the SSH port didn't open.")
                print "\n. I'm deleting instance:", instance.id
                conn.terminate_instances(instance_ids=[instance.id])
                return (False, None)
        
        """If we arrive here, then port 22 is open on the instance."""
         
        write_log(dbconn, "OK. Instance " + instance.id + " is running at " + instance.ip_address, code=0)
        add_job(dbconn, jobid)
        add_instance(dbconn, instance.id, instance.ip_address)
        map_job_on_instance(dbconn, jobid, instance.id)
        
        set_job_status(jobid, "Cloud resources online. Launching the analysis pipeline...")
        
        remote_command = "aws s3 cp s3://" + S3BUCKET + "/" + jobid.__str__() + " ./ --recursive --region " + ZONE
        print "AWS command:", remote_command
        ssh_command = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/.ssh/phylobot-ec2-key.pem ubuntu@" + instance.ip_address + "  '" + remote_command + "'"
        print "SSH command:", ssh_command
        os.system(ssh_command)
                
        """Run the startup script"""        
        remote_command = "bash slave_startup_script"
        ssh_command = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/.ssh/phylobot-ec2-key.pem ubuntu@" + instance.ip_address + "  '" + remote_command + "'"
        os.system( ssh_command )
        
        """Launch the job, using '&' to put the execution into the background"""
        remote_command = 'nohup bash exe </dev/null >command.log 2>&1 &'
        print "195:", remote_command
        ssh_command = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/.ssh/phylobot-ec2-key.pem ubuntu@" + instance.ip_address + "  '" + remote_command + "'"
        print "197:", ssh_command
        os.system( ssh_command )

        #
        # we need error checking here to ensure the ssh commands worked.
        #
                
        return (True, instance.id)
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        
        """An error occurred, so try to kill the instance."""
        write_log(dbconn, "There was a problem starting job " + jobid.__str__() + ". I'm terminating the instance " + instance.id.__str__(), code=0)
        conn.terminate_instances( instance_ids=[instance.id] )
        
        retid = None
        if instance != None:
            """Then kill the instance."""
            conn.terminate_instances(instance_ids=[instance.id])
            """And remove the mapping between this job and this instance"""
            remove_instance(dbconn, instance.id)

        return (False, retid)


def stop_job(jobid, dbconn):
    """dbconn is a connection to the job_daemon database."""
    
    """Does this job exist on any known instances?
        known_instances will be a list of instance IDs that, according to our database,
        may be running the job with id = jobid"""
    known_instances = get_instances_for_job(dbconn, jobid)
    if known_instances.__len__() == 0:
        print "\n. It appears that jobid " + jobid.__str__() + " has not been mapped to any instances."
        set_job_status(jobid, "Stopped")
        remove_job(dbconn, jobid)
        return True
    else:
        """Stop each of the known AWS EC2 instances. If the execution state has been saved,
            then it can be recovered from S3, but otherwise the execution state is lost forever."""
        logmsg = "Terminating the following instance(s) associated with job" + jobid.__str__() + ":" + known_instances.__str__()
        write_log(dbconn, logmsg, code=0)
        set_job_status(jobid, "Stopping cloud resources")
        conn = boto.ec2.connect_to_region(ZONE)   
        
        """Wait for AWS to catchup. Max wait is MAX_WAIT seconds"""
        time_count = 0
        MAX_WAIT = 120
        print "\n. Waiting for AWS to catchup"
        while(known_instances.__len__() > 0):
            """While our list of instances known to be associated with this jobid
                contains at least one non-terminated instance, then keep waiting for
                AWS to terminate."""
            all_instances = conn.get_all_instances()
            alive_instanceids = []
            for reservation in all_instances:
                ai = reservation.instances[0]
                if ai.state != "terminated":
                    """If the instance isn't terminated, then it's on our list."""
                    alive_instanceids.append( ai.id )
            
            """If putative instance IDs aren't running, then remove the instance from the list"""
            for id in known_instances:
                if id not in alive_instanceids:
                    known_instances.remove( id )
                    remove_instance(dbconn, id )
                    
            if known_instances.__len__() > 0:
                """Now try to terminate all of the remaining known_instances"""
                conn.terminate_instances(instance_ids=known_instances)        
            elif known_instances.__len__() == 0:
                """We're done!"""
                set_job_status(jobid, "Stopped")
                remove_job(dbconn, jobid)
                return True
            
            if time_count > MAX_WAIT:
                write_error(dbconn, "\n. Error 25 - The instance hasn't reach 'terminated' state after too long. jobid=" + jobid.__str__() )
                set_job_status(jobid, "Error evaporating clouds resources")
                return False
        
            time_count += 3
            time.sleep(3)
    
    return True

def release_job(jobid, dbconn):
    known_instances = get_instances_for_job(dbconn, jobid)
    if known_instances.__len__() == 0:
        print "\n. It appears that jobid " + jobid.__str__() + " has not been mapped to any instances."
        remove_job(dbconn, jobid)
        return True
    
    else:
        """Stop each of the known AWS EC2 instances. If the execution state has been saved,
            then it can be recovered from S3, but otherwise the execution state is lost forever."""
        logmsg = "Release cloud resources for jobid=" + jobid.__str__() + ":" + known_instances.__str__()
        write_log(dbconn, logmsg, code=0)
        conn = boto.ec2.connect_to_region(ZONE)   
        
        """Wait for AWS to catchup. Max wait is MAX_WAIT seconds"""
        time_count = 0
        MAX_WAIT = 120
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
            
            """If putative instance IDs aren't running, then remove the instance from the list"""
            for id in known_instances:
                if id not in alive_instanceids:
                    known_instances.remove( id )
                    remove_instance(dbconn, id )
                    
            if known_instances.__len__() > 0:
                """Now try to terminate all of the remaining known_instances"""
                conn.terminate_instances(instance_ids=known_instances)        
            elif known_instances.__len__() == 0:
                """We're done!"""
                remove_job(dbconn, jobid)
                return True
            
            if time_count > MAX_WAIT:
                write_error(dbconn, "\n. Error 311 - The instance hasn't reach 'terminated' state after too long. jobid=" + jobid.__str__() )
                set_job_status(jobid, "Error evaporating clouds resources")
                return False
        
            time_count += 3
            time.sleep(3)
    
    return True

def cleanup_orphaned_instances(dbconn):
    """Get a list of instances on EC2, and another list of known instances in our databse.
        Kill any instances on EC2 that don't map to a known job
    """
    conn = boto.ec2.connect_to_region(ZONE)
    reservations = conn.get_all_reservations()
    terminate_these_instance_ids = []
    for rr in reservations:
        for ii in rr.instances:
            #print ii.instance_type, ii.instance_type, ii.state, ii.ip_address
            
            if ii.state == "terminated":
                continue
            
            terminate_this_instance = False
            """Does this instance map to a known job?"""
            sql = "select jobid from JobInstance where aws_id='" + ii.id.__str__() + "'"
            cur = dbconn.cursor()
            #print "* Active Instance:", ii.id.__str__()
            cur.execute(sql)
            x = cur.fetchall()
            if x == None:
                """Then this instance has no known job."""
                terminate_this_instance = True
            else:
                for jj in x:
                    this_status = get_job_status( jj[0] )
                    if this_status.__contains__("Stopped"):
                        terminate_this_instance = True
                    elif this_status.__contains__("Finished"):
                        terminate_this_instance = True
            if terminate_this_instance == True:
                print "\n. 365 - planning to terminate instance for " + jj[0].__str__()
                terminate_these_instance_ids.append( ii.id )

    if terminate_these_instance_ids.__len__() > 0:
        print "369: Terminating:", terminate_these_instance_ids
        conn.terminate_instances( instance_ids=terminate_these_instance_ids ) 
                
def cleanup_orphaned_volumes(dbconn):
    conn = boto.ec2.connect_to_region(ZONE)
    volumes = conn.get_all_volumes(volume_ids=None, filters=None)      
    for volume in volumes:
        if volume.status == 'available':
            print "Deleting Volume:", volume.id
            volume.delete()

    