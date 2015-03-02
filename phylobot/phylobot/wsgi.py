
"""
WSGI config for phylobot project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
#Django 1.6:
#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phylobot.settings")
#Django 1.7:
os.environ['DJANGO_SETTINGS_MODULE'] = 'phylobot.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()




