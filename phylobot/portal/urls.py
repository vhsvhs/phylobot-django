from django.conf.urls import patterns, url

from portal import views
from portal.views import *
from portal.views_compose import *

urlpatterns = patterns('',
	(r'^composenew', composenew),
	(r'^compose1', compose1),
	(r'^compose2', compose2),
	(r'^cancelcompose', cancelcompose),
	(r'^compose/(.*)/$', edit_job),
	(r'^status/(.*)$', jobstatus),
	(r'^$', portal_main_page),
)

# urlpatterns = pattern('',
# 	(r,'^$', portal_offline),
# )