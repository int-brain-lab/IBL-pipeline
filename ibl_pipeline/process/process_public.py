import datajoint as dj
from ibl_pipeline.common import *
from ibl_pipeline import public
from ibl_pipeline.ingest import QueryBuffer
from tqdm import tqdm
from ibl_pipeline.process import (
    ingest_alyx_raw,
    ingest_shadow,
    ingest_membership,
    ingest_real,
    populate_behavior,
    populate_ephys,
    process_histology,
    populate_wheel
)
import logging

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("/src/IBL-pipeline/ibl_pipeline/process/logs/process_public.log"),
        logging.StreamHandler()],
    level=25)

logger = logging.getLogger(__name__)


def delete_non_published_records():

    with dj.config(safemode=False):

        logger.log(25, 'Deleting non-published probe insertions...')
        probe_insertion_table = QueryBuffer(ephys.ProbeInsertion)
        for key in tqdm(
                (ephys.ProbeInsertion - public.PublicProbeInsertion - ephys.DefaultCluster).fetch('KEY')):
            probe_insertion_table.add_to_queue1(key)
            if probe_insertion_table.flush_delete(quick=False, chunksz=100):
                logger.log(25, 'Deleted 100 probe insertions')

        probe_insertion_table.flush_delete(quick=False)
        logger.log(25, 'Deleted the rest of the probe insertions')

        logger.log(25, 'Deleting non-published sessions...')
        session_table = QueryBuffer(acquisition.Session)
        for key in tqdm(
                (acquisition.Session - public.PublicSession - behavior.TrialSet).fetch('KEY')):
            session_table.add_to_queue1(key)
            if session_table.flush_delete(quick=False, chunksz=100):
                logger.log(25, 'Deleted 100 sessions')

        session_table.flush_delete(quick=False)
        logger.log(25, 'Deleted the rest of the sessions')

        logger.log(25, 'Deleting non-published subjects...')
        subjs = subject.Subject & acquisition.Session

        for key in tqdm(
                (subject.Subject - public.PublicSubjectUuid - subjs.proj()).fetch('KEY')):
            (subject.Subject & key).delete()


def main(populate_only=False):

    if not populate_only:
        logger.log(25, 'Ingesting alyxraw...')
        ingest_alyx_raw.insert_to_alyxraw(
            ingest_alyx_raw.get_alyx_entries())
        logger.log(25, 'Ingesting shadow tables...')
        ingest_shadow.main()
        logger.log(25, 'Ingesting shadow membership...')
        ingest_membership.main()
        logger.log(25, 'Copying to real tables...')
        ingest_real.main()

        logger.log(25, 'Deleting the non published records...')
        delete_non_published_records()

    logger.log(25, 'Processing behavior...')
    populate_behavior.main(backtrack_days=1000)

    logger.log(25, 'Processing wheel...')
    populate_wheel.main(backtrack_days=1000)

    # logger.log(25, 'Processing ephys...')
    # populate_ephys.main()

    # logger.log(25, 'Processing histology...')
    # process_histology.populate_real_tables()
