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
# git clone https://github.com/vhsvhs/phylobot-django
# cd chipseqbot
# source aws_setup/config_master.sh --> launches this script
#

# Update apt-get
sudo apt-get -y update

# Install PIP
sudo apt-get -y install python-pip

#
# Install PostgreSQL
#
sudo apt-get -y install postgresql postgresql-contrib libpq-dev

sudo -u postgres psql -c "CREATE DATABASE csbotdb"

sudo -u postgres psql --dbname=csbotdb -c "CREATE USER django WITH PASSWORD 'phylobotpass'"
sudo -u postgres psql --dbname=csbotdb -c "ALTER ROLE django SET timezone TO 'UTC-8'"
sudo -u postgres psql --dbname=csbotdb -c "ALTER USER django CREATEDB"

sudo -u postgres psql --dbname=csbotdb -c "GRANT ALL PRIVILEGES ON DATABASE phylobotdb TO django"
sudo -u postgres psql --dbname=csbotdb -c "ALTER USER CREATEDB"

#
# Install Python packages
#
sudo apt-get -y install python-dev
sudo pip install -r requirements/prod.txt

# Ensure we have the latest version of Django-SES (Required to send email from Django)
sudo pip install django-ses

# Get the PhyloBot Django project
cd ~/
sudo rm -rf phylobot-django
git clone https://github.com/vhsvhs/phylobot-django

# Configure Apache to serve Django.
sudo cp ~/phylobot-django/aws_setup/phylobot.com.conf /etc/apache2/sites-enabled/

# Allow Apache (i.e. www-user) to write data into the
# media folder of the Django project. This is required
# in order for Apache to save uploaded files.
sudo chown -R www-data:www-data /home/ubuntu/phylobot-django/phylobot/static/media

# Add a softlink for the /admin app static files
sudo ln -s /usr/local/lib/python2.7/dist-packages/django/contrib/admin/static/admin phylobot-django/phylobot/static/admin

# Build the Django database
python phylobot-django/phylobot/manage.py syncdb

# Allow Apache write control of the Django database
sudo chown -R www-data:www-data ~/phylobot-django/phylobot/db.sqlite3
sudo chown -R www-data:www-data ~/phylobot-django/phylobot
sudo chmod a+x ~/phylobot-django/phylobot/phylobot/wsgi.py

# Run the populate_phylobot script to add things like
# known alignment algorithms, phylogenetic models, and job status
# objects to the DB.
sudo python phylobot-django/phylobot/populate_phylobot.py

#
# Optional: If you're cloning PhyloBot from another AWS instance,
# 	then run this script to copy all static media and data:
# sudo bash aws_setup/migrate.sh
#

