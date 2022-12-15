"""
This script inserts membership tuples into the membership shadow tables,
which cannot be inserted with auto-population.
"""

import itertools
import os

import datajoint as dj
import pymysql

from ibl_pipeline import mode
from ibl_pipeline.ingest import QueryBuffer, acquisition, action, alyxraw, data
from ibl_pipeline.ingest import get_raw_field as grf
from ibl_pipeline.ingest import reference, subject
from ibl_pipeline.utils import is_valid_uuid

MEMBERSHIP_TABLES = [
    {
        "dj_current_table": reference.ProjectLabMember,
        "alyx_parent_model": "subjects.project",
        "alyx_field": "users",
        "dj_parent_table": reference.Project,
        "dj_other_table": reference.LabMember,
        "dj_parent_fields": "project_name",
        "dj_other_field": "user_name",
        "dj_parent_uuid_name": "project_uuid",
        "dj_other_uuid_name": "user_uuid",
    },
    {
        "dj_current_table": subject.AlleleSequence,
        "alyx_parent_model": "subjects.allele",
        "alyx_field": "sequences",
        "dj_parent_table": subject.Allele,
        "dj_other_table": subject.Sequence,
        "dj_parent_fields": "allele_name",
        "dj_other_field": "sequence_name",
        "dj_parent_uuid_name": "allele_uuid",
        "dj_other_uuid_name": "sequence_uuid",
    },
    {
        "dj_current_table": subject.LineAllele,
        "alyx_parent_model": "subjects.line",
        "alyx_field": "alleles",
        "dj_parent_table": subject.Line,
        "dj_other_table": subject.Allele,
        "dj_parent_fields": "line_name",
        "dj_other_field": "allele_name",
        "dj_parent_uuid_name": "line_uuid",
        "dj_other_uuid_name": "allele_uuid",
    },
    {
        "dj_current_table": action.SurgeryProcedure,
        "alyx_parent_model": "actions.surgery",
        "alyx_field": "procedures",
        "dj_parent_table": action.Surgery,
        "dj_other_table": action.ProcedureType,
        "dj_parent_fields": ["subject_uuid", "surgery_start_time"],
        "dj_other_field": "procedure_type_name",
        "dj_parent_uuid_name": "surgery_uuid",
        "dj_other_uuid_name": "procedure_type_uuid",
    },
    {
        "dj_current_table": acquisition.ChildSession,
        "alyx_parent_model": "actions.session",
        "alyx_field": "parent_session",
        "dj_parent_table": acquisition.Session,
        "dj_other_table": acquisition.Session,
        "dj_parent_fields": ["subject_uuid", "session_start_time"],
        "dj_other_field": "session_start_time",
        "dj_parent_uuid_name": "session_uuid",
        "dj_other_uuid_name": "session_uuid",
        "renamed_other_field_name": "parent_session_start_time",
    },
    {
        "dj_current_table": acquisition.SessionUser,
        "alyx_parent_model": "actions.session",
        "alyx_field": "users",
        "dj_parent_table": acquisition.Session,
        "dj_other_table": reference.LabMember,
        "dj_parent_fields": ["subject_uuid", "session_start_time"],
        "dj_other_field": "user_name",
        "dj_parent_uuid_name": "session_uuid",
        "dj_other_uuid_name": "user_uuid",
    },
    {
        "dj_current_table": acquisition.SessionProcedure,
        "alyx_parent_model": "actions.session",
        "alyx_field": "procedures",
        "dj_parent_table": acquisition.Session,
        "dj_other_table": action.ProcedureType,
        "dj_parent_fields": ["subject_uuid", "session_start_time"],
        "dj_other_field": "procedure_type_name",
        "dj_parent_uuid_name": "session_uuid",
        "dj_other_uuid_name": "procedure_type_uuid",
    },
    {
        "dj_current_table": acquisition.SessionProject,
        "alyx_parent_model": "actions.session",
        "alyx_field": "project",
        "dj_parent_table": acquisition.Session,
        "dj_other_table": reference.Project,
        "dj_parent_fields": ["subject_uuid", "session_start_time"],
        "dj_other_field": "project_name",
        "dj_parent_uuid_name": "session_uuid",
        "dj_other_uuid_name": "project_uuid",
        "renamed_other_field_name": "session_project",
    },
    {
        "dj_current_table": data.ProjectRepository,
        "alyx_parent_model": "subjects.project",
        "alyx_field": "repositories",
        "dj_parent_table": reference.Project,
        "dj_other_table": data.DataRepository,
        "dj_parent_fields": "project_name",
        "dj_other_field": "repo_name",
        "dj_parent_uuid_name": "project_uuid",
        "dj_other_uuid_name": "repo_uuid",
    },
]

if mode != "public":
    MEMBERSHIP_TABLES.extend(
        [
            {
                "dj_current_table": action.WaterRestrictionUser,
                "alyx_parent_model": "actions.waterrestriction",
                "alyx_field": "users",
                "dj_parent_table": action.WaterRestriction,
                "dj_other_table": reference.LabMember,
                "dj_parent_fields": ["subject_uuid", "restriction_start_time"],
                "dj_other_field": "user_name",
                "dj_parent_uuid_name": "restriction_uuid",
                "dj_other_uuid_name": "user_uuid",
            },
            {
                "dj_current_table": action.WaterRestrictionProcedure,
                "alyx_parent_model": "actions.waterrestriction",
                "alyx_field": "procedures",
                "dj_parent_table": action.WaterRestriction,
                "dj_other_table": action.ProcedureType,
                "dj_parent_fields": ["subject_uuid", "restriction_start_time"],
                "dj_other_field": "procedure_type_name",
                "dj_parent_uuid_name": "restriction_uuid",
                "dj_other_uuid_name": "procedure_type_uuid",
            },
            {
                "dj_current_table": action.SurgeryUser,
                "alyx_parent_model": "actions.surgery",
                "alyx_field": "users",
                "dj_parent_table": action.Surgery,
                "dj_other_table": reference.LabMember,
                "dj_parent_fields": ["subject_uuid", "surgery_start_time"],
                "dj_other_field": "user_name",
                "dj_parent_uuid_name": "surgery_uuid",
                "dj_other_uuid_name": "user_uuid",
            },
            {
                "dj_current_table": acquisition.WaterAdministrationSession,
                "alyx_parent_model": "actions.wateradministration",
                "alyx_field": "session",
                "dj_parent_table": action.WaterAdministration,
                "dj_other_table": acquisition.Session,
                "dj_parent_fields": ["subject_uuid", "administration_time"],
                "dj_other_field": "session_start_time",
                "dj_parent_uuid_name": "wateradmin_uuid",
                "dj_other_uuid_name": "session_uuid",
            },
        ]
    )


def main(new_pks=None, excluded_tables=[]):
    for tab_args in MEMBERSHIP_TABLES:
        table_name = tab_args["dj_current_table"].__name__
        if table_name in excluded_tables:
            continue
        print(f"Ingesting table {table_name}...")
        ingest_membership_table(**tab_args, new_pks=new_pks)


def ingest_membership_table(
    dj_current_table,
    alyx_parent_model,
    alyx_field,
    dj_parent_table,
    dj_other_table,
    dj_parent_fields,
    dj_other_field,
    dj_parent_uuid_name,
    dj_other_uuid_name,
    renamed_other_field_name=None,
    new_pks=None,
):
    """
    Ingest shadow membership table.
    This function works for the pattern that an alyx parent model contain one or multiple entries of one field
    that have the information in the membership table.

    Arguments:  dj_current_table : datajoint table object, current membership table to ingest
                alyx_parent_model: string, model name inside alyx that contains information of the current table.
                alyx_field       : field of alyx that contains information of current table
                dj_parent_table  : datajoint parent table, corresponding to alyx parent model
                dj_other_table   : datajoint other table to fetch the field from
                dj_parent_fields : string or list of strings, field names to be fetched from the parent table
                dj_other_field   : string, the field table to be fetched from the other table
                dj_parent_uuid_name: string, uuid id name of the parent table
                dj_other_uuid_name: string, uuid id name of the other table
                renamed_other_field_name: string the other field name sometimes renamed in the real table,
                                        the default is None if the field is not renamed
                new_pks          : list of strings of valid uuids, this is the new entries to process, the
                                default is None if all entries are inserted.
    """
    if new_pks:
        restr = [{"uuid": pk} for pk in new_pks if is_valid_uuid(pk)]
    else:
        restr = {}

    alyxraw_to_insert = alyxraw.AlyxRaw & restr & {"model": alyx_parent_model}

    if not alyxraw_to_insert:
        return

    uuid_to_str_mysql = (
        f"CONVERT(LOWER(CONCAT("
        f"SUBSTR(HEX({dj_other_uuid_name}), 1, 8), '-',"
        f"SUBSTR(HEX({dj_other_uuid_name}), 9, 4), '-',"
        f"SUBSTR(HEX({dj_other_uuid_name}), 13, 4), '-',"
        f"SUBSTR(HEX({dj_other_uuid_name}), 17, 4), '-',"
        f"SUBSTR(HEX({dj_other_uuid_name}), 21))) USING utf8)"
    )

    if dj_other_uuid_name == dj_parent_uuid_name:
        dj_other_uuid_name = "other_" + dj_other_uuid_name

    # other table
    other_table_query = dj.U(
        dj_other_uuid_name, renamed_other_field_name or dj_other_field
    ) & dj_other_table.proj(
        **{
            dj_other_uuid_name: uuid_to_str_mysql,
            renamed_other_field_name or dj_other_field: dj_other_field,
        }
    )

    # parent-table
    if isinstance(dj_parent_fields, str):
        dj_parent_fields = [dj_parent_fields]

    parent_table_query = dj_parent_table.proj(*dj_parent_fields) * (
        alyxraw.AlyxRaw.Field
        & alyxraw_to_insert
        & {"fname": alyx_field}
        & 'fvalue!="None"'
    ).proj(..., **{dj_parent_uuid_name: "uuid", dj_other_uuid_name: "fvalue"})

    # join
    joined_tables = parent_table_query * other_table_query
    # insert
    try:
        dj_current_table.insert(
            joined_tables, ignore_extra_fields=True, skip_duplicates=True
        )
    except (pymysql.err.OperationalError, dj.errors.LostConnectionError) as e:
        # too many records to insert all at once on server side - do this in chunks
        attrs = [n for n in dj_current_table.heading.names if not n.endswith("_ts")]

        parent_table_entries = (
            dj.U(*[a for a in attrs if a in parent_table_query.heading.names])
            & parent_table_query
        ).fetch(as_dict=True)
        other_table_entries = (
            dj.U(*[a for a in attrs if a in other_table_query.heading.names])
            & other_table_query
        ).fetch(as_dict=True)

        current_table_buffer = QueryBuffer(dj_current_table)
        for parent_entry, other_entry in itertools.product(
            parent_table_entries, other_table_entries
        ):
            current_table_buffer.add_to_queue1({**parent_entry, **other_entry})
            current_table_buffer.flush_insert(skip_duplicates=True, chunksz=7500)

        current_table_buffer.flush_insert(skip_duplicates=True)


if __name__ == "__main__":
    main()
