#
# If you want to migrate from an old PhyloBot server to this (presumably new)
# AWS instance, then run this script after running setup_phylobot_server_on_aws.sh
#

# Copy the static data, including uploaded sequences.
cd
sudo chown www-data -R /home/ubuntu/phylobot-django/phylobot
sudo chgrp www-data -R /home/ubuntu/phylobot-django/phylobot

scp -i ~/.ssh/phylobot-ec2-key.pem -r ubuntu@www.phylobot.com:/home/ubuntu/phylobot-django/phylobot/static/* /home/ubuntu/phylobot-django/phylobot/static/
sudo chown www-data -R /home/ubuntu/phylobot-django/phylobot/static
sudo chgrp www-data -R /home/ubuntu/phylobot-django/phylobot/static

# Copy the main user and data DB. It's owned by www-data
scp -i ~/.ssh/phylobot-ec2-key.pem ubuntu@www.phylobot.com:/home/ubuntu/phylobot-django/phylobot/db.sqlite3 /home/ubuntu/phylobot-django/phylobot/
sudo chown www-data /home/ubuntu/phylobot-django/phylobot/db.sqlite3
sudo chgrp www-data /home/ubuntu/phylobot-django/phylobot/db.sqlite3

# Copy the Job daemon DB. It remains owned by root.
scp -i ~/.ssh/phylobot-ec2-key.pem ubuntu@www.phylobot.com:/home/ubuntu/phylobot-django/phylobot/job_daemon.db /home/ubuntu/phylobot-django/phylobot/

# Copy the BOTO configuration
sudo scp -i ~/.ssh/phylobot-ec2-key.pem -r ubuntu@www.phylobot.com:/etc/boto.cfg /etc/boto.cfg
sudo chown ubuntu /etc/boto.cfg
sudo chgrp ubuntu /etc/boto.cfg
