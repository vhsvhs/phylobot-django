import job_daemon_tools
from job_daemon_tools import *


print_splash()
"""dbconn is a connection to the daemon's DB (not the Django db)"""

dbconn = None
try:
    dbconn = build_db(SQLDBPATH)
    write_log(dbconn, "Connected to the daemon DB at " + SQLDBPATH.__str__())
    write_log(dbconn, "The PhyloBot job daemon is launching. . .")
except sqlite3.OperationalError:
    print "\n. Error, I couldn't open the database at " + SQLDBPATH
    print ". Try running this script as sudo."
    exit()

while(True):    
    """ Main Daemon Loop """
    conn = boto.sqs.connect_to_region(ZONE)
    queue = conn.get_queue("phylobot-jobs")
    if queue == None:
        queue = conn.create_queue("phylobot-jobs")
    
    """Get any messages on the SQS queue"""
    messages = queue.get_messages()
    if messages.__len__() > 0:
        print "\n. Daemon Status: There are ", messages.__len__().__str__(), "pending messages in the SQS queue."
    
    """
    Build a dictionary of jobs, actions, and their order in the queue.
    We'll use this ordering later on when we need to maintain queue state.
    """
    jobid_action_order = {}
    for ii in range(0, messages.__len__() ):
        msg = messages[ii]
        body = msg.get_body()
        tokens = body.split()
        if tokens.__len__() < 2:
            continue
        msg_action = tokens[0]
        msg_jobid = tokens[1]
        if msg_jobid not in jobid_action_order:
            jobid_action_order[msg_jobid] = {}
        jobid_action_order[msg_jobid][msg_action] = ii
    
    
    for msg in messages:
        """
        Deal with each message in the queue.
        """
        body = msg.get_body()
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
        
        print "\n. ", msg.attributes.__str__(), " SQS message:", body
        
        """If the message has been attempted too many times, delete it and skip to the next."""
        if msg_attempts > MAX_MSG_ATTEMPTS:
            print "\n. This message reached the maximum number of attempts without success. I'm deleting it forever."
            print body
            queue.delete_message( msg )
            continue
    
        if msg_action == "start":
            """
            start_job
            """
            (success_flag, aws_id) = start_job(msg_jobid, dbconn)
            if success_flag == False:
                write_log(dbconn, "I couldn't start the job " + msg_jobid.__str__() + ". I'm re-queing the job to try again next cycle.")
                
                """Here we delete the msg from the queue, increment the attempts counter,
                    then add the message back onto the queue."""
                queue.delete_message( msg )
                requeue = False
                """If there are no future/upstream SQS messages to stop the job, then let's
                    re-queue this failed job and increment its attempt counter."""
                if "stop" in jobid_action_order[msg_jobid]:
                    stoporder = jobid_action_order[msg_jobid]["stop"]
                    startoder = jobid_action_order[msg_jobid]["start"]
                    if stoporder < startoder: # if the stop was before the start request
                        requeue = True
                else:
                    requeue = True
                
                if requeue:
                    """Re-queue the msg with attempts += 1"""
                    sqs_start(msg_jobid, attempts=msg_attempts+1 )                
                continue
            else:
                """It didn't fail. Everything is OK. We can delete this queue message,
                    and presume that the job is now actively running."""
                queue.delete_message( msg )
                continue
  
        elif msg_action == "stop":
            """
            stop_job
            """
            success_flag = stop_job(msg_jobid, dbconn)
            queue.delete_message( msg )
            if success_flag == False:
                """It didn't successfully stop, so let's requeue this message and try again later"""
                set_job_status(jobid, "Re-trying the stop attempt.")
                sqs_stop(jobid, attempts=msg_attempts+1 )
            if success_flag == True:
                print "I successfully stopped job", msg_jobid
                set_job_status(msg_jobid, "Stopped")
            continue
        
        elif msg_action == "release":
            success_flag = release_job(msg_jobid, dbconn)
            queue.delete_message( msg )
            if success_flag == False:
                """It didn't successfully release, so let's requeue this message and try again later"""
                sqs_release(jobid, attempts=msg_attempts+1 )
            if success_flag == True:
                print "I successfully stopped job", msg_jobid
            continue
           
    """
    outside the for loop, but inside the while loop
    """
    time.sleep(6)
    cleanup_orphaned_instances(dbconn)
    cleanup_orphaned_volumes(dbconn)