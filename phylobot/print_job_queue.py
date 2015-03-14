import job_daemon_tools
from job_daemon_tools import *

"""
    This is the main loop for the daemon
"""
print_splash()
dbconn = build_db(SQLDBPATH)
write_log(dbconn, "Connected to the daemon DB at " + SQLDBPATH.__str__())
  
conn = boto.sqs.connect_to_region(ZONE)
queue = conn.get_queue("phylobot-jobs")
if queue == None:
    queue = conn.create_queue("phylobot-jobs")

"""Get any messages on the SQS queue"""
messages = queue.get_messages()
if messages.__len__() > 0:
    print "\n. Daemon Status: There are ", messages.__len__().__str__(), "pending messages in the SQS queue."
else:
    print "\n. The queue is empty."

for msg in messages:
    """For each queue message:"""
    body = msg.get_body()
    
    print "Message:", body