'''
This script inserts tuples in the alyxraw table into the shadow tables \
via auto-populating.
'''

import datajoint as dj
from ibl.ingest import alyxraw, reference, subject, action, acquisition, data

# reference tables
reference.Lab.populate()
reference.LabMember.populate()
reference.LabMembership().populate()
reference.LabLocation().populate()
reference.Project().populate()

# subject tables
subject.Species.populate()
subject.Source.populate()
subject.Strain.populate()
subject.Sequence.populate()
subject.Allele.populate()
subject.Line.populate()
subject.Subject.populate()
subject.BreedingPair.populate()
subject.Litter.populate()
subject.LitterSubject.populate()
subject.Weaning.populate()
subject.Death.populate()
subject.GenotypeTest.populate()
subject.Zygosity.populate()
subject.Implant.populate()

# action tables
action.ProcedureType.populate()
action.Weighing.populate()
action.WaterAdministration.populate()
action.WaterRestriction.populate()
action.Surgery.populate()
action.OtherAction.populate()

# acquisition tables
acquisition.Session.populate()

# data tables
data.DataFormat().populate()
data.DataRepositoryType.populate()
data.DataRepository.populate()
data.DataSetType.populate()
data.DataSet.populate()
data.FileRecord.populate()
