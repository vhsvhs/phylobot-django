#
# This script should be run when the PhyloBot server 
# instance is launched for the first time.
#

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
# Optional: If you're cloning PhyloBot from another instance,
# run this too:
# sudo bash aws_setup/migrate.sh
#

