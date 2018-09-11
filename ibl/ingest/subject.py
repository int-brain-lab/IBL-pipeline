
import datajoint as dj

from . import reference

from .. import subject as ds_subject

schema = dj.schema('ibl_ingest_subject')


@schema
class Species(dj.Computed):
    definition = ds_subject.Species.definition


@schema
class Strain(dj.Computed):
    definition = ds_subject.Strain.definition


@schema
class Sequence(dj.Computed):
    definition = ds_subject.Sequence.definition


@schema
class AlleleSequence(dj.Computed):
    definition = ds_subject.AlleleSequence.definition


@schema
class Line(dj.Computed):
    definition = ds_subject.Line.definition


@schema
class LineAllele(dj.Computed):
    definition = ds_subject.LineAllele.definition


@schema
class Subject(dj.Computed):
    definition = ds_subject.Subject.definition


@schema
class BreedingPair(dj.Computed):
    definition = ds_subject.BreedingPair.definition


@schema
class Litter(dj.Computed):
    definition = ds_subject.Litter.definition

@schema
class LitterSubject(dj.Computed):
    definition = ds_subject.LitterSubject.definition


@schema
class Weighing(dj.Computed):
    definition = ds_subject.Weighing.definition


@schema
class WaterAdministration(dj.Computed):
    definition = ds_subject.WaterAdministration.definition


@schema
class Caging(dj.Computed):
    definition = ds_subject.Caging.definition


@schema
class Weaning(dj.Computed):
    definition = ds_subject.Weaning.definition


@schema
class GenotypeTest(dj.Computed):
    definition = ds_subject.GenotypeTest.definition


@schema
class Zygosity(dj.Computed):
    definition = ds_subject.Zygosity.definition


@schema
class Surgery(dj.Computed):
    definition = ds_subject.Surgery.definition


@schema
class Implant(dj.Computed):
    definition = ds_subject.Implant.definition


@schema
class VirusInjection(dj.Computed):
    definition = ds_subject.VirusInjection.definition


@schema
class Culling(dj.Computed):
    definition = ds_subject.Culling.definition


@schema
class Reduction(dj.Computed):
    definition = ds_subject.Reduction.definition


@schema
class Reduction(dj.Computed):
    definition = ds_subject.Reduction.definition


@schema
class OtherAction(dj.Computed):
    definition = ds_subject.OtherAction.definition


@schema
class Death(dj.Computed):
    definition = ds_subject.Death.definition


