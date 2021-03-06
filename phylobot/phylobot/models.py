from django.db import models
from django.contrib.auth.models import User
from portal.random_primary import *

class UserProfile(models.Model):
    # This line is required. Links UserProfile to a User model instance.
    user = models.OneToOneField(User)
    firstname = models.CharField(max_length=30,blank=True)
    lastname = models.CharField(max_length=40,blank=True)

    # Override the __unicode__() method to return out something meaningful!
    def __unicode__(self):
        return self.user.username   

class ViewingPrefs(models.Model):
    """The class ViewingPrefs stores specifications about, for example,
        the last-viewed model, the last-viewed alignment, etc.
        This allows the web interface to directly load the last-viewed
        setting rather than requiring the user to re-setup their view space."""
    libid = models.IntegerField() # the ancestral library ID
    keyword = models.CharField(max_length=35)
    value = models.CharField(max_length=100)
    user = models.ForeignKey(User)    
    
    
#class AncestralLibrary(models.Model):
class AncestralLibrary(RandomPrimaryIdModel):
    """This class stores paths to sqlite3 DBs that were computed by the asrpipeline.
        All PhyloBot jobs, upon completion, will get an entry in this table."""
    
    # 'id' is depricated -- now randomly generated by the RandomPrimaryIdModel
    #id = models.IntegerField(primary_key=True)
    _FIRSTIDCHAR = string.digits
    _IDCHARS = string.digits
    CRYPT_KEY_LEN_MIN = 9
    CRYPT_KEY_LEN_MAX = 15
    
    shortname = models.CharField(max_length=30)
    contact_authors_profile = models.ManyToManyField(UserProfile) # these users will be listed on the frontpage of the public library view
    dbpath = models.FileField(upload_to='anclibs')
    last_modified = models.DateTimeField(auto_now=True)
        
    def __unicode__(self):
        return unicode(self.shortname)  

class AncestralLibraryVisibility(models.Model):
    libid = models.ForeignKey(AncestralLibrary)
    visibility = models.IntegerField() # 0 = only visible to owner, 1 = visible to world

class AncestralLibraryPermissions(models.Model):
    libid = models.ForeignKey(AncestralLibrary)
    user = models.ForeignKey(User)
    permission = models.IntegerField() # 0 = no access, 1 = edit access, 2 = re-run and admin access
    
class AncestralLibrarySourceJob(models.Model):
    """This class maps PhyloBot jobs to imported Ancestral Libraries"""
    libid = models.IntegerField() # the ancestral library ID
    jobid = models.CharField(max_length=30) # the job ID