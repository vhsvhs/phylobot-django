from django.conf.urls import patterns, include, url
from django.contrib import auth
from django.contrib import admin
admin.autodiscover()

from phylobot import views
from phylobot.view_library import view_library
from phylobot.view_faqs import *

urlpatterns = patterns('', 
	(r'^$', views.main_page),
	
 	(r'^admin/', include(admin.site.urls)),
	(r'^accounts/', include('allauth.urls') ),

 	(r'^contact/$', views.contact),
 	(r'^notice/$', views.beta_notice),
 	(r'^about/$', views.about),
 	(r'^examples/$', views.examples),
 	(r'^overview/$', views.overview),
 	(r'^portal/', include('portal.urls')),
 	(r'^status*', include('portal.urls')),	
 	(r'^faq_fasta*', faq_fasta),
 	(r'^faq_newick*', faq_newick),
	
	#
	# continue here!
	#
	
		

# 	These patterns are depricated, because we're not using the allauth package.
# 	(r'^login/$', 'django.contrib.auth.views.login'),
#   (r'^logout/$', views.logout_page),
# 	(r'^register/$', views.register), # ADD NEW PATTERN!

#  
# 	#Note: the method named 'view_library' performs further URL dispatching.
# 	#	In the future, that code should be moved to this urls.py file."""
 	(r'^(.*)/.*$', view_library),	
 	(r'^(.*)$', view_library),

)
