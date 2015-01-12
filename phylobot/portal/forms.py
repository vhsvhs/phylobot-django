from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from portal.models import *

from django.forms.widgets import CheckboxSelectMultiple, Select, CheckboxInput
from django.forms.models import ModelMultipleChoiceField

class JobSettingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        self.fields["alignment_algorithms"].widget = CheckboxSelectMultiple() 
        self.fields["alignment_algorithms"].queryset = AlignmentAlgorithm.objects.all()
        self.fields["alignment_algorithms"].initial = AlignmentAlgorithm.objects.all()
        self.fields['alignment_algorithms'].label = "Use the following alignment algorithms"
        self.fields['alignment_algorithms'].help_text = ""
        
        self.fields["raxml_models"].widget = CheckboxSelectMultiple() 
        self.fields["raxml_models"].queryset = RaxmlModel.objects.all()
        self.fields['raxml_models'].initial = RaxmlModel.objects.all()
        self.fields['raxml_models'].help_text = ""
        self.fields['raxml_models'].label = "Try the following RAxML models"
        
        self.fields['name'].label = "Name this job"
        self.fields['project_description'].label = "Project description (optional)"

    class Meta:
        model = JobSetting
        fields = ('name',
                  'project_description',
                  'alignment_algorithms',
                  'raxml_models',
                  'start_motif',
                  'end_motif',
                  'n_bayes_samples',
                  )

class SeqFileForm(forms.ModelForm):    
    def __init__(self, *args, **kwargs):
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        self.fields["seq_path"].label = "Select a FASTA file"
    class Meta:
        model = SeqFile
        fields = ('seq_path',)
        
class TaxaGroupForm(forms.ModelForm):
    """This form displays a TaxaGroup, which includes a list of taxon names,
    and a name for this group."""    
    #taxa = forms.CheckboxSelectMultiple()
    #name = forms.CharField(max_length=30)
    
    def __init__(self, *args, **kwargs):
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        self.fields["taxa"].widget = CheckboxSelectMultiple()
        self.fields["taxa"].help_text = ''
        self.fields["taxa"].label = "Select one or more taxon"
        self.fields["name"].label = "Create a name for this group"
    class Meta:
        model = TaxaGroup
        fields = ('taxa','name',)

class OutgroupForm(forms.ModelForm):        
    def __init__(self, *args, **kwargs):  
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        self.fields['outgroup'].label = "Select an outgroup"
        self.fields['outgroup'].widget = Select()
    class Meta:
        model = JobSetting
        fields = ('outgroup',)
    
class AncestorForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        self.fields["ingroup"].label = "Select an 'in' group"
        self.fields["ancname"].label = "Name"
        self.fields["ancname"].help_label = "Create a name for this ancestor"
        self.fields["seedtaxa"].label = "Seed Taxon"
        self.fields["seedtaxa"].help_label = "Select an extant 'seed' sequence for this ancestor"
        
    class Meta:
        model = Ancestor
        fields = ('ancname',
                  'seedtaxa',
                  'ingroup',)

class AncCompForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        self.fields["oldanc"].label = "Old Ancestor"
        self.fields["newanc"].label = "Descendant Ancestor"
    
    """A form to create new ancestral comparisons"""
    class Meta:
        model = AncComp
        fields = ('oldanc', 'newanc')
        
