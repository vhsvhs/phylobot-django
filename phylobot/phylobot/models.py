from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    # This line is required. Links UserProfile to a User model instance.
    user = models.OneToOneField(User)
    firstname = models.CharField(max_length=30,blank=True)
    lastname = models.CharField(max_length=40,blank=True)

    # The additional attributes we wish to include.
    website = models.URLField(blank=True)
    labwebsite = models.URLField(blank=True)
    picture = models.ImageField(upload_to='profile_images', blank=True)

    # Override the __unicode__() method to return out something meaningful!
    def __unicode__(self):
        return self.user.username   
    

class AncestralLibrary(models.Model):
    """This class stores paths to sqlite3 DBs that were computed by the asrpipeline.
        All PhyloBot jobs, upon completion, will get an entry in this table."""
    id = models.IntegerField(primary_key=True)
    shortname = models.CharField(max_length=30)
    contact_authors_profile = models.ManyToManyField(UserProfile) # these users will be listed on the frontpage of the public library view
    dbpath = models.FileField(upload_to='anclibs')
    last_modified = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return unicode(self.shortname)  

class AncestralLibraryPermissions(models.Model):
    libid = models.ForeignKey(AncestralLibrary)
    user = models.ForeignKey(User)
    permission = models.IntegerField() # 0 = no access, 1 = edit access, 2 = re-run and admin access