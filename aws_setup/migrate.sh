#
# If you want to migrate from the old PhyloBot server to this (presumably new)
# server, then run this script after running setup_phylobot_server_on_aws.sh
#

# Copy the static data, including uploaded sequences.
cd
scp -i ~/.ssh/phylobot-ec2-key.pem -r ubuntu@phylobot:/home/ubuntu/phylobot-django/phylobot/static/* /home/ubuntu/phylobot-django/phylobot/static/
sudo chown www-data -r /home/ubuntu/phylobot-django/phylobot/static
sudo chgrp www-data -r /home/ubuntu/phylobot-django/phylobot/static

# Copy the main user and data DB. It's owned by www-data
scp -i ~/.ssh/phylobot-ec2-key.pem ubuntu@phylobot:/home/ubuntu/phylobot-django/phylobot/db.sqlite3 /home/ubuntu/phylobot-django/phylobot/
sudo chown www-data -r /home/ubuntu/phylobot-django/phylobot/db.sqlite3
sudo chgrp www-data -r /home/ubuntu/phylobot-django/phylobot/db.sqlite3

# Copy the Job daemon DB. It remains owned by root.
scp -i ~/.ssh/phylobot-ec2-key.pem ubuntu@phylobot:/home/ubuntu/phylobot-django/phylobot/job_daemon.db /home/ubuntu/phylobot-django/phylobot/
