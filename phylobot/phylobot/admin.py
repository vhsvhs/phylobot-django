from django.contrib import admin
admin.autodiscover()
from phylobot.models import UserProfile

print "\n\n\n phylobot admin\n\n\n"
admin.site.register(UserProfile)