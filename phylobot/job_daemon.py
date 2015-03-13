import job_daemon_tools
from job_daemon_tools import *

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
        """For each queue message:"""
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
            (success_flag, aws_id) = start_job(msg_jobid, dbconn)
            
            """Did the 'start' action fail?"""
            if success_flag == False:
                write_log(con, "aws_id is None after starting job " + msg_jobid.__str__() + ". I'm re-queing the job to try again next cycle.")
                
                """Here we delete the msg from the queue, increment the attempts counter,
                    then add the message back onto the queue."""
                queue.delete_message( msg )
                
                """Re-queue the msg with attempts += 1"""
                sqs_start(msg_jobid, attempts=msg_attempts+1 )                
                continue
            else:
                """It didn't fail. Everything is OK. We can delte this queue message"""
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
