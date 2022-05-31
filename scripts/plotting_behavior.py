"""
This script populate all behavioral plotting table for the website
"""

import datajoint as dj
from tqdm import tqdm

from ibl_pipeline import reference, subject
from ibl_pipeline.plotting import behavior

if __name__ == "__main__":

    kwargs = dict(suppress_errors=True, display_progress=True)

    print("------------ Populating plotting.SessionPsychCurve -----------")
    behavior.SessionPsychCurve.populate(**kwargs)
    print("------ Populating plotting.SessionReactionTimeContrast -------")
    behavior.SessionReactionTimeContrast.populate(**kwargs)
    print("---- Populating plotting.SessionReactionTimeTrialNumber ------")
    behavior.SessionReactionTimeTrialNumber.populate(**kwargs)
    print("--------------- Populating plotting.DatePsychCurve -----------")
    behavior.DatePsychCurve.populate(**kwargs)
    print("-------- Populating plotting.DateReactionTimeContrast --------")
    behavior.DateReactionTimeContrast.populate(**kwargs)
    print("------ Populating plotting.DateReactionTimeTrialNumber -------")
    behavior.DateReactionTimeTrialNumber.populate(**kwargs)
    print("--------------- Populating plotting.WaterTypeColor -----------")
    behavior.WaterTypeColor.populate(**kwargs)

    print(
        "------------ Populating plotting.CumulativeSummary and update SubjectLatestDate -----------"
    )

    print("Processing Cumulative plots...")
    with dj.config(safemode=False):
        (
            behavior.CumulativeSummary
            & behavior.CumulativeSummary.get_outdated_entries().fetch("KEY")
        ).delete()
    behavior.CumulativeSummary.populate(**kwargs)

    print("Update SubjectLatestDate...")
    subject_latest_date = subject.Subject.aggr(
        behavior.CumulativeSummary, latest_date="MAX(latest_date)"
    )
    behavior.SubjectLatestDate.insert(subject_latest_date, skip_duplicates=True)

    need_update = (
        behavior.SubjectLatestDate.proj(inserted_date="latest_date")
        * subject_latest_date
        & "inserted_date != latest_date"
    )
    for k in need_update.fetch("KEY"):
        (behavior.SubjectLatestDate & k)._update1(
            "latest_date", (subject_latest_date & k).fetch1("latest_date")
        )
