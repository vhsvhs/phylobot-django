from django.db import models

class AWSConfiguration(models.Model):
    """This class stores information that is necessary to run Amazon Web Services."""

    """And ID for this configuration."""
    id = models.IntegerField(primary_key=True)

    """e.g. us-west-1"""
    preferred_region = models.CharField(max_length=20, blank=True)
    
    """The instance ID of the compute nodes"""
    compute_instance_id = models.CharField(max_length=40, blank=True)
    
    """e.g. t1.micro"""
    compute_instance_type = models.CharField(max_length=30, blank=True)
    
    """The ID of a snapshot to start a new instance."""
    compute_snapshot_id = models.CharField(max_length=40, blank=True)

    """The access key_name used to create instances."""
    key_name = models.CharField(max_length=40, blank=True)

    """ e.g., 'phylobot-security' """
    compute_security_group = models.CharField(max_length=40, blank=True)

    """The bucket into which work gets written. For example 'phylbot.s3' """
    s3_bucket = models.CharField(max_length=100, blank=True)
    
    """The key prefix used for storing ancestral libraries.
        e.g. '/asrlibs/'
    """
    s3_asrlib_key_prefix = models.CharField(max_length=100, blank=True)
    

    def __unicode__(self):
        return unicode(self.id)  