from django.contrib import admin

# Register your models here.
from portal.models import *
admin.site.register(SeqType)
admin.site.register(Taxon)
admin.site.register(AlignmentAlgorithm)
admin.site.register(RaxmlModel)
admin.site.register(TaxaGroup)
admin.site.register(Ancestor)
admin.site.register(AncComp)
admin.site.register(SeqFileFormat)
admin.site.register(AASeqFile)
admin.site.register(CodonSeqFile)
admin.site.register(Job)
admin.site.register(JobSetting)
admin.site.register(JobQueue)
admin.site.register(QueueOp)
admin.site.register(SoftwarePaths)
