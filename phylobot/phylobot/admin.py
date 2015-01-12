from django.contrib import admin
admin.autodiscover()
from phylobot.models import *

print "\n\n\n phylobot admin\n\n\n"
admin.site.register(UserProfile)
admin.site.register(AncestralLibrary)