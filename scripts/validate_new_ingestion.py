import datajoint as dj
import pandas as pd

from ibl_pipeline import (
    acquisition,
    action,
    data,
    ephys,
    histology,
    qc,
    reference,
    subject,
)
from ibl_pipeline.ingest import acquisition as shadow_acquisition
from ibl_pipeline.ingest import action as shadow_action
from ibl_pipeline.ingest import data as shadow_data
from ibl_pipeline.ingest import ephys as shadow_ephys
from ibl_pipeline.ingest import histology as shadow_histology
from ibl_pipeline.ingest import job
from ibl_pipeline.ingest import qc as shadow_qc
from ibl_pipeline.ingest import reference as shadow_reference
from ibl_pipeline.ingest import subject as shadow_subject

real_vmods = {}
for m in (reference, subject, action, acquisition, data, ephys, qc, histology):
    assert m.schema.database.startswith("test_")
    schema_name = m.__name__.split(".")[-1]
    real_vmods[schema_name] = dj.create_virtual_module(
        schema_name, m.schema.database[5:]
    )


def main(start="2022-01-20", end="2022-01-22", verbose=True):
    session_res = f'session_start_time BETWEEN "{start}" AND "{end}"'

    vm_session_keys_for_missing = (
        real_vmods["acquisition"].Session & session_res
    ).fetch("KEY")
    session_keys_for_missing = (
        acquisition.Session
        & [
            {"session_uuid": u}
            for u in (real_vmods["acquisition"].Session & session_res).fetch(
                "session_uuid"
            )
        ]
    ).fetch("KEY")

    session_keys_for_extra = (acquisition.Session & session_res).fetch("KEY")
    vm_session_keys_for_extra = (
        real_vmods["acquisition"].Session
        & [
            {"session_uuid": u}
            for u in (acquisition.Session & session_res).fetch("session_uuid")
        ]
    ).fetch("KEY")

    discrepancy = {}
    for full_table_name, table_detail in job.DJ_TABLES.items():
        real_table = table_detail["real"]
        if real_table is None:
            continue

        schema_name, table_name = full_table_name.split(".")
        vm_real_table = getattr(real_vmods[schema_name], table_name)

        if table_name in ("Session"):
            missing = len(vm_real_table & vm_session_keys_for_missing) - len(
                real_table & session_keys_for_missing
            )
            extra = len(real_table & session_keys_for_extra) - len(
                vm_real_table & vm_session_keys_for_extra
            )
        else:
            missing = len(
                (vm_real_table & vm_session_keys_for_missing)
                - (real_table & session_keys_for_missing).proj()
            )
            extra = len(
                (real_table & session_keys_for_extra)
                - (vm_real_table & vm_session_keys_for_extra).proj()
            )

        discrepancy[full_table_name] = {"missing": missing, "extra": extra}

    discrepancy = pd.DataFrame(discrepancy).T
    if verbose:
        print(discrepancy)
    return discrepancy
