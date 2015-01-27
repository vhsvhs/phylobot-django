from django.contrib import admin
admin.autodiscover()
from phylobot.models import *
from phylobot.models_aws import *

print "\n\n\n phylobot admin\n\n\n"
admin.site.register(UserProfile)
admin.site.register(AncestralLibrary)
admin.site.register(AWSConfiguration)
admin.site.register(ViewingPrefs)
