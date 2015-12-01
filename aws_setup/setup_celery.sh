#
# Setup Celery
#
sudo pip install -U Celery
pip install django-celery

cd $PHYLOBOT_REPO/phylobot

# Star the Celery worker:
celery -A phylobot worker -l info