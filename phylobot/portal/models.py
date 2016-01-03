from django.db import models
from django.contrib.auth.models import User
import datetime
from django.conf import settings
import os, random, string
from random_primary import *
import aws_tools
from django.forms.fields import *

class SoftwarePaths(models.Model):
    """This model holds executable paths to various software tools, including RAxML, PhyML, clustal, etc."""
    softwarename = models.CharField(max_length=50)
    path = models.TextField()
    
    def __unicode__(self):
        return unicode(self.path)

class SeqType(models.Model):
    id = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=30)
    short = models.CharField(max_length=5)

    def __unicode__(self):
        return unicode(self.short)

class Taxon(models.Model):
    name = models.CharField(max_length=100)
    seqtype = models.ForeignKey(SeqType)
    nsites = models.IntegerField()
    
    def __unicode__(self):
        return unicode(self.name)

class TaxonNCBI(models.Model):
    """If the given fasta file is NCBI-formatted, then we may have the following information
        (based on http://www.uniprot.org/help/fasta-headers)
    """
    taxon = models.ForeignKey(Taxon)
    uniqueid = models.CharField(max_length=20)
    entryname = models.CharField(max_length=40)
    proteinname = models.CharField(max_length=40, null=True)
    organismname = models.CharField(max_length=50, null=True)
    genename = models.CharField(max_length=30, null=True)
    proteinexistence = models.IntegerField(null=True)
    sequenceversion = models.IntegerField(null=True)
    
    def __unicode__(self):
        return unicode(self.uniqueid)
    
class AlignmentAlgorithm(models.Model):
    name = models.CharField(max_length=30)
    executable = models.TextField()
    def __unicode__(self):
        return unicode(self.name)

class RaxmlModel(models.Model):
    name = models.CharField(max_length=30)
    def __unicode__(self):
        return unicode(self.name)

class TaxaGroup(models.Model):
    taxa = models.ManyToManyField(Taxon)
    taxa.help_text = ''
    name = models.CharField(max_length=30)
    owner = models.ForeignKey(User)
    
    def __unicode__(self):
        return unicode(self.name)
    
    def listall(self):
        r = ""
        for t in self.taxa.all():
            r += t.__str__() + ","
        r = r[0:-1]
        return r
    
    def clear_all(self):
        for t in self.taxa.all():
            self.taxa.remove(t)

class Ancestor(models.Model):
    ancname = models.CharField(max_length=30)
    seedtaxa = models.ForeignKey(Taxon)
    ingroup = models.ForeignKey(TaxaGroup, related_name='ingroup')
    outgroup = models.ForeignKey(TaxaGroup)
      
    def __unicode__(self):
        return unicode(self.ancname)

class AncComp(models.Model):
    oldanc = models.ForeignKey(Ancestor, related_name='oldanc')
    newanc = models.ForeignKey(Ancestor, related_name='newanc')
    
    def __unicode__(self):
        return unicode(self.oldanc.ancname + " to " + self.newanc.ancname)

class SeqFileFormat(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=30)

    def __unicode__(self):
        return unicode(self.name) 


class AASeqFile(models.Model):
    aaseq_path = models.FileField(upload_to='uploaded_sequences')
    format = models.ForeignKey(SeqFileFormat,null=True)
    owner = models.ForeignKey(User)
    timestamp_uploaded = models.DateTimeField(auto_now=True)
    contents = models.ManyToManyField(Taxon,null=True)
    contents.help_text = ''
    
    def __unicode__(self):
        return unicode(self.aaseq_path)    

class CodonSeqFile(models.Model):
    codonseq_path = models.FileField(upload_to='uploaded_sequences')
    format = models.ForeignKey(SeqFileFormat,null=True)
    owner = models.ForeignKey(User)
    timestamp_uploaded = models.DateTimeField(auto_now=True)
    contents = models.ManyToManyField(Taxon,null=True)
    contents.help_text = ''
    
    def __unicode__(self):
        return unicode(self.codonseq_path) 

class ConstraintTreeFile(models.Model):
    constrainttree_path = models.FileField(upload_to='uploaded_sequences')
    owner = models.ForeignKey(User)
    timestamp_uploaded = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return unicode(self.constrainttree_path) 
    
#class CustomeAlignmentFile(models.Model):
#    customalignment_path = models.FileField(upload_to='uploaded_sequences')
#    owner = models.ForeignKey(Users)
#    timestamp_uploaded = models.DateTimeField(auto_now=True)
#    
#    def __unicode__(self):
#        return unicode(self.customalignment_path)

class JobSetting(models.Model):
    """Defines the settings for an ASR pipeline job."""
    outgroup = models.ForeignKey(TaxaGroup, related_name="outgroup",null=True)
    name = models.CharField(max_length=100,null=True)
    project_description = models.TextField(null=True)
    original_aa_file = models.ForeignKey( AASeqFile,null=True,related_name="aa_file" )
    has_codon_data = models.BooleanField(default=False)
    original_codon_file = models.ForeignKey( CodonSeqFile,null=True,related_name="codon_file" )
    constraint_tree_file = models.ForeignKey( ConstraintTreeFile, null=True )
    alignment_algorithms = models.ManyToManyField(AlignmentAlgorithm,null=True)
    alignment_algorithms.help_text = ''
    raxml_run = models.TextField(null=True)
    raxml_models = models.ManyToManyField(RaxmlModel,null=True)
    raxml_models.help_text = ''
    phyml_run = models.TextField(null=True)
    mpirun_run = models.TextField(null=True)
    lazarus_run = models.TextField(null=True)
    markov_model_folder = models.FilePathField(null=True)
    anccomp_run = models.TextField(null=True)
    pdbtools_dir = models.FilePathField(null=True)
    pymol_run = models.TextField(null=True)
    use_mpi = models.BooleanField(default=False)
    start_motif = models.CharField(max_length=20,null=True)
    end_motif = models.CharField(max_length=20,null=True)
    n_bayes_samples = models.IntegerField(default=100,null=True)
    phyre_output = models.FileField(upload_to='phyre_output',null=True)
    taxa_groups = models.ManyToManyField(TaxaGroup,null=True)
    ancestors = models.ManyToManyField(Ancestor,null=True)
    anc_comparisons = models.ManyToManyField(AncComp,null=True)
    anc_comparisons.help_text = ''
    
    def is_valid(self):
        """Error checks the values. Returns True if all is OK."""
        return True

    def __unicode__(self):
        return unicode(self.name) 

ID_FIELD_LENGTH = 16
    
def byte_to_base32_chr(byte):
    return alphabet[byte & 31]

def random_id(length):
    # Can easily be converted to use secure random when available
    # see http://www.secureprogramming.com/?action=view&feature=recipes&recipeid=20
    random_bytes = [random.randint(0, 0xFF) for i in range(length)]
    return ''.join(map(byte_to_base32_chr, random_bytes))
    
class Job(RandomPrimaryIdModel):
    """ A job can be any executable task. It can be an invocation of software, like Muscle,
    or it can be a call to a shell script, like source X.
    """
    #id = models.CharField(primary_key=True, max_length=ID_FIELD_LENGTH)
    owner = models.ForeignKey(User)
    settings = models.ForeignKey(JobSetting,null=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    exe = models.TextField(null=True) # this is the shell command used to invoke the job.
    path = models.TextField(null=True) # this is the directory path in which output from this job is written
    
    note = models.TextField(null=True) # notes about the job, in addition to its status, can be written here.
    checkpoint = models.FloatField(null=True)
    p_done = models.FloatField(null=True) # percentage done. THis is used for display purposes only, dynamically calculated based on the S3 'checkpoint' key
        
    def __unicode__(self):
        if self.settings != None:
            if self.settings.name != None:
                return unicode(self.settings.name)
        return unicode(self.owner)

    def validate(self):
        """Checks that everything is okay with the job. If it's ready to launch,
        then this method returns True. If there are errors, this method returns False.
        If the job is okay, then the output folder for the job will be created."""
        allokay = True

        """Does this job have valid settings?"""
        if False == self.settings.is_valid():
            allokay = False

        if allokay:
            
            """Working directory for the project"""
            self.path = settings.MEDIA_ROOT + "/" + self.id.__str__()
            if False == os.path.exists( self.path ):
                """Make it"""
                os.system("mkdir " + self.path)
            
            """amino acid file"""
            os.system("cp " + settings.MEDIA_ROOT.__str__() + "/" + self.settings.original_aa_file.__str__() + " " + self.path.__str__() + "/" + self.settings.name.__str__() + ".erg.aa.fasta")            

            """codon file (optional)"""
            if self.settings.has_codon_data == True:
                os.system("cp " + settings.MEDIA_ROOT.__str__() + "/" + self.settings.original_codon_file.__str__() + " " + self.path.__str__() + "/" + self.settings.name.__str__() + ".erg.codon.fasta")  
        return True

    def generate_configfile(self):
        """This script generates the config file, necessary for the ASR pipeline."""
        cout = "GENE_ID = " + self.settings.name + "\n"
        cout += "PROJECT_TITLE = " + self.settings.name + "\n" 
        
        aapath = self.settings.original_aa_file.aaseq_path._get_path().split("/")[  self.settings.original_aa_file.aaseq_path._get_path().split("/").__len__()-1 ]
        cout += "SEQUENCES = " + aapath + "\n" 
        if self.settings.has_codon_data == True:
            codonpath = self.settings.original_codon_file.aaseq_path._get_path().split("/")[  self.settings.original_codon_file.aaseq_path._get_path().split("/").__len__()-1 ]
            cout += "NTFASTA = " + codonpath + "\n"
        cout += "MSAPROBS = " + SoftwarePaths.objects.get(softwarename="msaprobs").__str__() + "\n"
        cout += "MUSCLE = " + SoftwarePaths.objects.get(softwarename="muscle").__str__() + "\n"
        cout += "RAXML = " + SoftwarePaths.objects.get(softwarename="raxml").__str__() + "\n" 
        cout += "PHYML = " + SoftwarePaths.objects.get(softwarename="phyml").__str__() + "\n"
        cout += "LAZARUS = " + SoftwarePaths.objects.get(softwarename="lazarus").__str__() + "\n"
        cout += "ANCCOMP = " + SoftwarePaths.objects.get(softwarename="anccomp").__str__() + "\n"
        cout += "ZORRO = " + SoftwarePaths.objects.get(softwarename="zorro").__str__() + "\n"
        cout += "FASTTREE = " + SoftwarePaths.objects.get(softwarename="fasttree").__str__() + "\n"
        cout += "MARKOV_MODEL_FOLDER = " + SoftwarePaths.objects.get(softwarename="markov_models").__str__() + "\n"
        cout += "USE_MPI = False\n"
        cout += "RUN = sh\n"
        cout += "ALIGNMENT_ALGORITHMS ="
        for aa in self.settings.alignment_algorithms.all():
            cout += " " + aa.name.__str__()
        cout += "\n"
        cout += "MODELS_RAXML ="
        for mr in self.settings.raxml_models.all():
            cout += " " + mr.name.__str__()
        cout += "\n"
        if self.settings.start_motif:
            cout += "START_MOTIF = " + self.settings.start_motif + "\n"
        if self.settings.end_motif:
            cout += "END_MOTIF = " + self.settings.end_motif + "\n"
        cout += "N_BAYES_SAMPLES = 0\n"
        cout += "OUTGROUP = [" + (TaxaGroup.objects.get(id=self.settings.outgroup.id)).listall() + "]\n"
        cout += "ANCESTORS ="
        for a in self.settings.ancestors.all():
            cout += " " + a.ancname.__str__()
        cout += "\n"
        for a in self.settings.ancestors.all():
            cout += "INGROUP "
            cout += a.ancname.__str__() + " "
            cout += "[" + a.ingroup.listall() + "]\n"
            cout += "ASRSEED "
            cout += a.ancname.__str__() + " "
            cout += a.seedtaxa.__str__() + "\n"
        for c in self.settings.anc_comparisons.all():
            cout += "COMPARE " + c.oldanc.ancname.__str__() + " " + c.newanc.ancname.__str__() + "\n"
        if self.settings.constraint_tree_file:
            cout += "CONSTRAINT_TREE = " + self.settings.constraint_tree_file.constrainttree_path._get_path().split("/")[  self.settings.constraint_tree_file.constrainttree_path._get_path().split("/").__len__()-1 ]
        
        configpath = self.path + "/" + self.id.__str__() + ".config"
        fout = open(configpath, "w")
        fout.write(cout)
        fout.close()
        return configpath

    def generate_exe(self, jumppoint = None, stoppoint = None):
        """Generates a shell-executable command that will invoke the job.
        NOTE: this method assumes that validate() was called, and returned True."""
        configpath = self.generate_configfile()
        self.exe = ""
                
        self.exe += SoftwarePaths.objects.get(softwarename="asrpipeline").__str__()
        self.exe += " --configpath " + self.id.__str__() + ".config"
        if jumppoint != None:
            self.exe += " --jump " + jumppoint.__str__()
        if stoppoint != None:
            self.exe += " --stop " + stoppoint.__str__()
        self.exe += " --enable_aws True"
        self.exe += " --s3_bucket " + aws_tools.S3BUCKET.__str__() # phylobot-jobfiles"
        self.exe += " --s3_keybase " + self.id.__str__()
        if self.checkpoint:
            self.exe += " --jump " + self.checkpoint.__str__()
        self.save()


    