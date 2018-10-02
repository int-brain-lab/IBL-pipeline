import datajoint as dj
from ibl.ingest import alyxraw, reference, subject, action

reference.LabMember().populate()
reference.Location().populate()
reference.Note().populate()

subject.Source().populate()
subject.Strain().populate()
subject.Sequence().populate()
subject.Allele().populate()
subject.Line().populate()
subject.BreedingPair().populate()
subject.Litter().populate()
subject.Subject().populate()
subject.Caging().populate()
subject.Weaning().populate()
subject.Culling().populate()
subject.Reduction().populate()
subject.Death().populate()
subject.GenotypeTest().populate()
subject.Zygosity().populate()
subject.Implant().populate()


action.ProcedureType().populate()
action.Weighing().populate()
action.WaterAdministration().populate()
action.WaterRestriction().populate()
action.Surgery().populate()
action.OtherAction().populate()

