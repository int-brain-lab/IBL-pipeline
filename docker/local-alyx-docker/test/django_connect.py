import django

django.setup()

from actions.models import Session
from subjects.models import Subject

# TODO: Better Django example usage

if __name__ == "__main__":
    database = "default"
    subj_ids = Subject.objects.using("default").values_list("id", flat=True)
    session = Session.objects.using(database).filter(subject_id=list(set(subj_ids))[0])
