from django.conf.urls import patterns, include, url
from django.contrib import auth
from django.contrib import admin
admin.autodiscover()

from phylobot import views
from phylobot.view_library import view_library

urlpatterns = patterns('', 
	(r'^$', views.main_page),
	
	#(r'^accounts/', include('allauth.urls')),
	(r'^accounts/', include('allauth.urls') ),
		
# 	# Login / logout
 	(r'^admin/', include(admin.site.urls)),
# 	(r'^login/$', 'django.contrib.auth.views.login'),
#   (r'^logout/$', views.logout_page),
 	(r'^contact/$', views.contact),
# 	(r'^blog/$', views.blog),
 	(r'^about/$', views.about),
# 	(r'^register/$', views.register), # ADD NEW PATTERN!
 	(r'^examples/$', views.examples),
 	(r'^overview/$', views.overview),
#  	
 	(r'^portal/', include('portal.urls')),
 	(r'^status*', include('portal.urls')),	
#  
# 	#Note: the method named 'view_library' performs further URL dispatching.
# 	#	In the future, that code should be moved to this urls.py file."""
 	(r'^(.*)/.*$', view_library),	
 	(r'^(.*)$', view_library),

)
