################################################################
#
# This script should be run when the PhyloBot server 
# instance is launched for the first time.
# 
# Before running this script, read the instructions located in 
# the file named "documentation/setup server notes.txt"
#
# REQUIREMENTS:
# This script retrieves secret keys from environmental variables.
# Contact your system admin. to retrieve the appropriate keys.
#
# INSTRUCTIONS:
# sudo apt-get -y install git
# sudo rm -rf phylobot-django
# git clone https://github.com/vhsvhs/phylobot-django
# cd phylobot-django
# source aws_setup/setup_phylobot_server_on_aws.sh
#
###########################################################

# Load environment variables:
source ~/.phylobot

# Update apt-get and PIP
sudo apt-get -y update
sudo apt-get -y install python-pip

# Install and Setup PostgreSQL
cd $PHYLOBOT_REPO
source aws_setup/setup_postgresql.sh

# Install Python packages
sudo apt-get -y install python-dev
sudo pip install -r requirements/prod.txt

# (legacy) Stop Apache if it's running, b/c now we're
# using Nginx and Gunicorn.
sudo service apache2 stop

# Setup Nginx
cd $PHYLOBOT_REPO
source aws_tools/setup_nginx.sh

# (legacy)
# Add a softlink for the /admin app static files
sudo ln -s /usr/local/lib/python2.7/dist-packages/django/contrib/admin/static/admin phylobot-django/phylobot/static/admin

# Setup Static files
cd $PHYLOBOT_REPO/phylobot
python manage.py collectstatic # move css, js, etc. into the appropriate assets folder

# Build the Django Database
python manage.py syncdb

# Run the populate_phylobot script to add things like
# known alignment algorithms, phylogenetic models, and job status
# objects to the DB.
python populate_phylobot.py

# Migrate all data from the previous PhyloBot
# Disable this line if you want a totally fresh PhyloBot.
sudo bash aws_setup/migrate.sh

# Setup Celery & RabbitMQ
cd $PHYLOBOT_REPO
source aws_setup/setup_rabbitmq.sh
source aws_setup/setup_celery.sh

# Setup Upstart to auto-launch PhyloBot
source aws_setup/setup_upstart.sh
