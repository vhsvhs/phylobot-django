from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from phylobot import views
from view_library import *

urlpatterns = patterns('', 
	(r'^$', views.main_page),
	
	# Login / logout
	(r'^admin/', include(admin.site.urls)),
	(r'^login/$', 'django.contrib.auth.views.login'),
    (r'^logout/$', views.logout_page),
	(r'^contact/$', views.contact),
	(r'^blog/$', views.blog),
	(r'^about/$', views.about),
	(r'^register/$', views.register), # ADD NEW PATTERN!
	(r'^examples/$', views.examples),
	
	(r'^portal/', include('portal.urls')),

	(r'^(.*)/$', view_library),
	(r'^(.*)$', view_library),
	
)
