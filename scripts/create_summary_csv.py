"""
This script creates a summary of the training status of animals in each lab.
"""

from datetime import datetime

import datajoint as dj
import numpy as np
import pandas as pd

from ibl_pipeline import acquisition, action, behavior, data, reference, subject
from ibl_pipeline.analyses import behavior as behavior_analyses

if __name__ == "__main__":
    for ilab in reference.Lab:
        ingested_sessions = (
            acquisition.Session & "task_protocol is not NULL" & behavior.TrialSet
        )
        subjects = (
            ((subject.Subject * subject.SubjectLab & ilab) - subject.Death)
            & 'sex != "U"'
            & action.Weighing
            & action.WaterAdministration
            & ingested_sessions
        )

        if not len(subjects):
            continue

        last_sessions = (
            subjects.aggr(
                ingested_sessions,
                "subject_nickname",
                session_start_time="max(session_start_time)",
            )
            * acquisition.Session
            * behavior_analyses.SessionTrainingStatus
        )

        filerecord = data.FileRecord & subjects & 'relative_path LIKE "%alf%"'
        last_filerecord = subjects.aggr(
            filerecord, latest_session_on_flatiron="max(session_start_time)"
        )

        summary = (
            (last_sessions * last_filerecord)
            .proj(
                "subject_nickname",
                "task_protocol",
                "training_status",
                "latest_session_on_flatiron",
            )
            .fetch(as_dict=True)
        )

        for entry in summary:
            subj = subject.Subject & entry
            protocol = entry["task_protocol"].partition("ChoiseWorld")[0]
            entry["latest_session_ingested"] = entry.pop("session_start_time")
            entry["latest_task_protocol"] = entry.pop("task_protocol")
            entry["latest_training_status"] = entry.pop("training_status")
            # get all sessions with this protocol
            entry["n_sessions"] = len(
                ingested_sessions & subj & 'task_protocol LIKE "{}%"'.format(protocol)
            )

        summary = pd.DataFrame(summary)
        summary.sort_values("subject_nickname", inplace=True, ascending=True)
        summary.pop("subject_uuid")
        summary.index += 1
        cols = summary.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        summary = summary[cols]
        last_session_date = (
            np.max(summary["latest_session_ingested"]).date().strftime("%Y-%m-%d")
        )
        summary.to_csv(
            "/src/IBL-pipeline/snapshots/{}_{}_summary.csv".format(
                last_session_date, ilab["lab_name"]
            ),
            index=False,
        )
        print("Saved {} current training status summary.".format(ilab["lab_name"]))
