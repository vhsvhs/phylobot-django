"""
This script builds a compute slave as an Amazon Web Services Instance.
In the future, this script should get incorporated into the job queue process,
but for now it can live here.
"""

import boto
import boto.ec2
import time


def launch_new_instance():
    pass



#################################################
#
# main
#
print "\n. Connecting to EC2..."
conn = boto.ec2.connect_to_region("us-west-1")

