#
# This script should be run when the PhyloBot server 
# instance is launched for the first time.
# 
# Run this script as part of the instructions located in the file
# named "documentation/setup server notes.txt"
#
# see documentation/setup server notes.txt for more information.
#
# REQUIREMENTS:
# This script retrieves secret keys from environmental variables.
# Contact your system admin. to retrieve the appropriate keys.
#
# USAGE on a fresh Ubuntu machine (first read REQUIREMENTS):
#
# sudo apt-get -y install git
# sudo rm -rf phylobot-django
# git clone https://github.com/vhsvhs/phylobot-django
# cd phylobot-django
# source aws_setup/setup_phylobot_server_on_aws.sh --> launches this script
#

source ~/.phylobot

#
# Update apt-get
#
sudo apt-get -y update

#
# Install PIP
#
sudo apt-get -y install python-pip

#
# Install PostgreSQL
#
sudo apt-get -y install postgresql postgresql-contrib libpq-dev
sudo -u postgres psql -c "CREATE DATABASE phylobotdb"
sudo -u postgres psql --dbname=phylobotdb -c "CREATE USER django WITH PASSWORD 'phylobotpass'"
sudo -u postgres psql --dbname=phylobotdb -c "ALTER ROLE django SET timezone TO 'UTC-8'"
sudo -u postgres psql --dbname=phylobotdb -c "ALTER USER django CREATEDB"
sudo -u postgres psql --dbname=phylobotdb -c "GRANT ALL PRIVILEGES ON DATABASE phylobotdb TO django"
sudo -u postgres psql --dbname=phylobotdb -c "ALTER USER CREATEDB"

#
# Install Python packages
#
sudo apt-get -y install python-dev
sudo pip install -r requirements/prod.txt

# (legacy)
# stop Apache
#
sudo service apache2 stop

#
# Install Nginx
# (In Ubuntu, nginx will auto start upon installation)
#
sudo apt-get -y install nginx
sudo mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.old
sudo cp aws_setup/nginx.conf /etc/nginx/nginx.conf

#
# Launch Nginx with the new configuration.
# Because nginx is launched upon installation (in previous steps), 
# we need to restart nginx to ensure that correct configurations
# are loaded.
#
sudo /etc/init.d/nginx stop
sudo /etc/init.d/nginx reload
sudo /etc/init.d/nginx start

# (depricated - this is now done in the requirements text)
# Ensure we have the latest version of Django-SES (Required to send email from Django)
#sudo pip install django-ses

#
# Get the PhyloBot Django project
#
cd ~/
sudo rm -rf phylobot-django
git clone https://github.com/vhsvhs/phylobot-django

# (depricated - we're now using Nginx and Gunicorn)
# Configure Apache to serve Django.
#sudo cp ~/phylobot-django/aws_setup/phylobot.com.conf /etc/apache2/sites-enabled/

# (depricated)
# Allow Apache (i.e. www-user) to write data into the
# media folder of the Django project. This is required
# in order for Apache to save uploaded files.
#sudo chown -R www-data:www-data /home/ubuntu/phylobot-django/phylobot/static/media

# (legacy)
# Add a softlink for the /admin app static files
#
sudo ln -s /usr/local/lib/python2.7/dist-packages/django/contrib/admin/static/admin phylobot-django/phylobot/static/admin

#
# Setup Static files
#
cd ~/phylobot-django/phylobot
python manage.py collectstatic # move css, js, etc. into the appropriate assets folder

#
# Build the Django Database
#
python manage.py syncdb

#
# Run the populate_phylobot script to add things like
# known alignment algorithms, phylogenetic models, and job status
# objects to the DB.
#
python populate_phylobot.py

# (depricated)
# Allow Apache write control of the Django database
#sudo chown -R www-data:www-data ~/phylobot-django/phylobot/db.sqlite3
#sudo chown -R www-data:www-data ~/phylobot-django/phylobot
#sudo chmod a+x ~/phylobot-django/phylobot/phylobot/wsgi.py

#
# Optional: If you're cloning PhyloBot from another AWS instance,
# 	then run this script to copy all static media and data:
# sudo bash aws_setup/migrate.sh
#

#
# Launch the Job Daemon
#
cd ~/phylobot-django
sudo chmod 755 phylobot/job_daemon.py
sudo cp aws_setup/jobdaemon.init.script /etc/init/jobdaemon.conf
sudo chmod 755 /etc/init/jobdaemon.conf
sudo initctl reload-configuration
sudo start jobdaemon

#
# Launch Gunicorn
# (errors will be written to the log @ /var/log/upstart/gunicorn.log)
#
cd ~/phylobot-django
sudo cp aws_setup/gunicorn.init.script /etc/init/gunicorn.conf
sudo chmod 755 /etc/init/gunicorn.conf
sudo initctl reload-configuration
sudo start gunicorn

# (depricated)
#cd ~/phylobot-django/phylobot
#gunicorn -w 4 phylobot.wsgi
