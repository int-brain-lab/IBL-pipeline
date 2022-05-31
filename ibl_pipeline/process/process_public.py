"""
This module process public data release to the public server.
It should be run in the docker container set up with docker-compose-public.yml
"""

import logging
import warnings
from os import get_blocking
from pathlib import Path

import datajoint as dj
import numpy as np
from tqdm import tqdm

from ibl_pipeline import public
from ibl_pipeline.common import *
from ibl_pipeline.ingest import QueryBuffer
from ibl_pipeline.process import (
    ingest_alyx_raw,
    ingest_membership,
    ingest_real,
    ingest_shadow,
    populate_behavior,
    populate_ephys,
    populate_wheel,
    process_histology,
)

# TODO: change /data /tmp to use dj.config
logging.basicConfig(
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler(
            "/src/IBL-pipeline/ibl_pipeline/process/logs/process_public.log"
        ),
        logging.StreamHandler(),
    ],
    level=25,
)


# logger does not work without this somehow
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)


logger = logging.getLogger(__name__)


def get_env_data_as_dict(env_path: str) -> dict:
    with open(env_path, "r") as f:
        return dict(
            tuple(line.replace("\n", "").split("="))
            for line in f.readlines()
            if not line.startswith("#") and line != "\n"
        )


def ingest_uuid_into_public_tables(uuid_datapath):
    """This function ingests uuids for subjects (public.PublicSubjectUuid),
        sessions (public.PublicSession), and probe insertions (public.PublicProbeInsertion)
        into public tables, in both internal and public databases

    Args:
        uuid_datapath (str): datapath storing uuids for subjects and sessions
            ready for publishing, looking for files subject_eids, session_eids,
            probeinsertion_eids. An example of uuid_datapath inside docker container:
            /src/IBL-pipeline/public_data_release/202106_data_paper_ines
    """

    # set up connections for both internal and public databases
    # credentials configured in .env_public
    conn_public = dj.conn()

    # load credentials for internal database instance
    # TODO: change /data /tmp to use dj.config
    internal_env = get_env_data_as_dict("/src/IBL-pipeline/.env")
    conn_internal = dj.conn(
        internal_env["DJ_HOST"], internal_env["DJ_USER"], internal_env["DJ_PASS"]
    )

    # public schema in the internal database
    public_schema_internal = dj.create_virtual_module(
        "public_internal", "ibl_public", connection=conn_internal
    )
    public_schema_public = dj.create_virtual_module(
        "public_public", "ibl_public", connection=conn_public
    )

    # internal subject schema
    subject = dj.create_virtual_module(
        "subject", "ibl_subject", connection=conn_internal
    )
    # internal acquisition schema
    acquisition = dj.create_virtual_module(
        "acquisition", "ibl_acquisition", connection=conn_internal
    )

    # ingest into public.PublicSubjectUuid
    subject_eid_files = list(Path(uuid_datapath).glob("*subject_eids*"))
    if not subject_eid_files:
        warnings.warn("subject_eids file does not exist")
    else:
        for f in subject_eid_files:
            subject_uuids = np.load(f, allow_pickle=True)
            # fetch subject information from subject.Subject table in internal database
            subjects_to_release = (
                (
                    subject.Subject * subject.SubjectLab
                    & [{"subject_uuid": uuid} for uuid in subject_uuids]
                )
                .proj("lab_name", "subject_nickname")
                .fetch(as_dict=True)
            )
            # ingest into internal PublicSubjectUuid
            public_schema_internal.PublicSubject.insert(
                subjects_to_release, skip_duplicates=True, ignore_extra_fields=True
            )
            public_schema_internal.PublicSubjectUuid.insert(
                subjects_to_release, skip_duplicates=True, allow_direct_insert=True
            )

            # ingest into public PublicSubjectUuid
            public_schema_public.PublicSubjectUuid.insert(
                subjects_to_release, skip_duplicates=True, allow_direct_insert=True
            )

    # ingest into public.PublicSession
    session_eid_files = list(Path(uuid_datapath).glob("*session_eids*"))
    if not session_eid_files:
        warnings.warn("session_eids file does not exist")
    else:
        for f in session_eid_files:
            session_uuids = np.load(f, allow_pickle=True)
            # fetch session information from acquisition.Session table in the internal database
            sessions_to_release = (
                (
                    acquisition.Session
                    & [{"session_uuid": uuid} for uuid in session_uuids]
                )
                .proj("session_uuid")
                .fetch(as_dict=True)
            )
            # ingest into internal PublicSession
            public_schema_internal.PublicSession.insert(
                sessions_to_release, skip_duplicates=True
            )

            # ingest into public PublicSession
            public_schema_public.PublicSession.insert(
                sessions_to_release, skip_duplicates=True
            )

    # ingest into public.PublicProbeInsertion
    probe_insertion_eid_files = list(Path(uuid_datapath).glob("*probe_insertion_eids*"))
    if not probe_insertion_eid_files:
        warnings.warn("probe_insertion_eids file does not exist")
    else:
        for f in probe_insertion_eid_files:
            probe_insertion_uuids = np.load(f, allow_pickle=True)
            probe_insertions_to_release = [
                {"probe_insertion_uuid": uuid} for uuid in probe_insertion_uuids
            ]
            # ingest into internal PublicProbeInsertion
            public_schema_internal.PublicProbeInsertion.insert(
                probe_insertions_to_release, skip_duplicates=True
            )

            # ingest into public PublicProbeInsertion
            public_schema_public.PublicProbeInsertion.insert(
                probe_insertions_to_release, skip_duplicates=True
            )


def delete_non_published_records():

    with dj.config(safemode=False):

        logger.log(25, "Deleting non-published probe insertions...")
        probe_insertion_table = QueryBuffer(ephys.ProbeInsertion)
        for key in tqdm(
            (
                ephys.ProbeInsertion
                - public.PublicProbeInsertion
                - ephys.DefaultCluster
            ).fetch("KEY")
        ):
            probe_insertion_table.add_to_queue1(key)
            if probe_insertion_table.flush_delete(quick=False, chunksz=100):
                logger.log(25, "Deleted 100 probe insertions")

        probe_insertion_table.flush_delete(quick=False)
        logger.log(25, "Deleted the rest of the probe insertions")

        logger.log(25, "Deleting non-published sessions...")
        session_table = QueryBuffer(acquisition.Session)
        for key in tqdm(
            (acquisition.Session - public.PublicSession - behavior.TrialSet).fetch(
                "KEY"
            )
        ):
            session_table.add_to_queue1(key)
            if session_table.flush_delete(quick=False, chunksz=100):
                logger.log(25, "Deleted 100 sessions")

        session_table.flush_delete(quick=False)
        logger.log(25, "Deleted the rest of the sessions")

        logger.log(25, "Deleting non-published subjects...")
        subjs = subject.Subject & acquisition.Session

        for key in tqdm(
            (subject.Subject - public.PublicSubjectUuid - subjs.proj()).fetch("KEY")
        ):
            (subject.Subject & key).delete()


# TODO: change /data /tmp to use dj.config
def main(populate_only=False, populate_wheel=False, populate_ephys_histology=False):
    """This function process the all the steps to get data ingested into the public database, needs rewriting
        to load data from sql dump instead.

    Args:
        populate_only (bool, optional): If True, only populate table; if False, start from the beginning
            and load entries from alyx dump in the folder /data. Defaults to False.
        populate_wheel (bool, optional): If True, populate wheel
        populate_ephys_histology (bool, optional): If True, populate ephys and histology tables
    """

    if not populate_only:
        # logger.log(25, 'Ingesting alyxraw...')
        # ingest_alyx_raw.insert_to_alyxraw(
        #     ingest_alyx_raw.get_alyx_entries())
        logger.log(25, "Ingesting shadow tables...")
        ingest_shadow.main()
        logger.log(25, "Ingesting shadow membership...")
        ingest_membership.main()
        logger.log(25, "Copying to real tables...")
        ingest_real.main()

        logger.log(25, "Deleting the non published records...")
        delete_non_published_records()

    logger.log(25, "Processing behavior...")
    populate_behavior.main(backtrack_days=1000)

    if populate_wheel:
        logger.log(25, "Processing wheel...")
        populate_wheel.main(backtrack_days=1000)

    if populate_ephys_histology:
        logger.log(25, "Processing ephys...")
        populate_ephys.main()

        logger.log(25, "Processing histology...")
        process_histology.populate_real_tables()
