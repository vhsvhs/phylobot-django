#
# This script will solve the situation in which you've changed the portal model,
# and launched a new PhyloBot server instance running the new model on an empty
# database. How do we import all the previous data from the previous PhyloBot instance,
# which is running the old model code?
#
# This script will download the old models and data from PhyloBot,
# setup the initial migration on that data, and run a fake migration
# to establish the migration data chain.
#
# Then, this script will run migrations on the new model, and update
# the old database to the new migrated models.
#

source ~/.phylobot

cp portal/models.py portal/models.py.newphylobot
cp portal/admin.py portal/admin.py.newphylobot

scp -i ~/.ssh/phylobot-ec2-key.pem ubuntu@phylobot.com:/home/ubuntu/phylobot-django/phylobot/portal/models.py portal/models.py
scp -i ~/.ssh/phylobot-ec2-key.pem ubuntu@phylobot.com:/home/ubuntu/phylobot-django/phylobot/portal/admin.py portal/admin.py
scp -i ~/.ssh/phylobot-ec2-key.pem ubuntu@phylobot.com:/home/ubuntu/phylobot-django/phylobot/db.sqlite3 ./db.sqlite3

rm -rf portal/migrations
rm -rf phylobot/migraions

python manage.py makemigrations portal
python manage.py migrate portal --fake

#
# Now make the real migration
#
cp portal/models.py.newphylobot portal/models.py
cp portal/admin.py.newphylobot portal/admin.py

python manage.py makemigrations portal
python manage.py migrate portal