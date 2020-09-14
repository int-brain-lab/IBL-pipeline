'''
This module delete the entries from alyxraw, shadow tables and update real tables
'''
import datajoint as dj
from ibl_pipeline.process.ingest_membership import membership_tables
from ibl_pipeline.common import *
from ibl_pipeline.ingest.common import *
from ibl_pipeline.ingest import job, InsertBuffer
from ibl_pipeline.ingest import ingest_utils
from ibl_pipeline import update
from uuid import UUID
from tqdm import tqdm


# ====================================== functions for deletion ===================================

def is_valid_uuid(uuid):
    try:
        UUID(uuid)
        return True
    except ValueError:
        return False


def delete_entries_from_alyxraw(pks_to_be_deleted):
    '''
    Delete entries from alyxraw and shadow tables, excluding the membership table.
    '''
    # TODO: this function to be tested
    print('Deleting entries from alyxraw ...')

    main_buffer = alyxraw.AlyxRaw

    for pk in tqdm(pks_to_be_deleted, position=0):
        if is_valid_uuid(pk):
            main_buffer.delete1({'uuid': pk})
            main_buffer.flush_delete(skip_duplicates=True, chunksz=50)

    main_buffer.flush_delete()

def delete_entries_from_membership(pks_to_be_deleted):
    '''
    Delete entries from shadow membership tables
    '''
    for t in membership_tables:
        ingest_mod = t['dj_parent_table'].__module__
        table_name = t['dj_parent_table'].__name__

        mem_table_name = t['dj_current_table'].__name__

        print(f'Deleting from table {mem_table_name} ...')
        real_table = eval(ingest_mod.replace('ibl_pipeline.ingest.', '') + '.' + table_name)

        (t['dj_current_table'] &
         (real_table &
          [{t['dj_parent_uuid_name']:pk}
           for pk in pks_to_be_deleted if is_valid_uuid(pk)]).fetch('KEY')).delete()


# =================================== functions for update ==========================================

TABLES_TO_UPDATE = [
    {'real_schema': reference,
     'shadow_schema': reference_ingest,
     'table_name': 'Project',
     'members': []
    },
    {'real_schema': subject,
     'shadow_schema': subject_ingest,
     'table_name': 'Subject',
     'members': ['SubjectLab', 'SubjectUser', 'SubjectProject', 'Death']
    },
    {'real_schema': action,
     'shadow_schema': action_ingest,
     'table_name': 'Weighing',
     'members': []
    },
    {'real_schema': action,
     'shadow_schema': action_ingest,
     'table_name': 'WaterRestriction',
     'members': []
    },
    {'real_schema': action,
     'shadow_schema': action_ingest,
     'table_name': 'WaterAdministration',
     'members': []
    },
    {'real_schema': acquisition,
     'shadow_schema': acquisition_ingest,
     'table_name': 'Session',
     'members': ['SessionUser', 'SessionProject']
    }
]

def update_fields(real_schema, shadow_schema, table_name, pks, insert_to_table=False):
    '''
    Given a table and the primary key of real table, update all the fields that have discrepancy.
    Inputs: real_schema     : real schema module, e.g. reference
            shadow_schema   : shadow schema module, e.g. reference_ingest
            table_name      : string, name of a table, e.g. Subject
            pks             : list of dictionaries, primary keys of real table that contains modification
            insert_to_table : boolean, if True, log the update histolory in the table ibl_update.UpdateRecord
    '''

    real_table = getattr(real_schema, table_name)
    shadow_table = getattr(shadow_schema, table_name)

    secondary_fields = set(real_table.heading.secondary_attributes)
    ts_field = [f for f in secondary_fields
                  if '_ts' in f][0]
    fields_to_update = secondary_fields - {ts_field}

    for r in (real_table & pks).fetch('KEY'):

        pk_hash = UUID(dj.hash.hash_key_values(r))

        if not shadow_table & r:
            try:
                (real_table & r).delete()
                if insert_to_table:
                    delete_record = dict(
                        table=real_table.__module__ + '.' + real_table.__name__,
                        pk_hash=pk_hash,
                        original_ts=real_record[ts_field],
                        deleted=1,
                    )
                    update.DeleteRecord.insert1(delete_record)
            except BaseException as e:
                print(f'Error while deleting record {r}: {str(e)}')

            continue

        shadow_record = (shadow_table & r).fetch1()
        real_record = (real_table & r).fetch1()


        for f in fields_to_update:
            if real_record[f] != shadow_record[f]:
                try:
                    dj.Table._update(real_table & r, f, shadow_record[f])
                    update_narrative=f'{table_name}.{f}: {shadow_record[f]} != {real_record[f]}'
                    print(update_narrative)
                    if insert_to_table:
                        update_record = dict(
                            table=real_table.__module__ + '.' + real_table.__name__,
                            attribute=f,
                            pk_hash=pk_hash,
                            original_ts=real_record[ts_field],
                            update_ts=shadow_record[ts_field],
                            pk_dict=r,
                            original_value=real_record[f],
                            updated_value=shadow_record[f],
                            update_narrative=update_narrative
                        )
                        update.UpdateRecord.insert1(update_record)

                except BaseException as e:
                    print(f'Error while updating record {r}: {str(e)}')


def update_entries_from_real_tables(modified_pks):

    for table in TABLES_TO_UPDATE:

        t = table.copy()
        table = getattr(t['real_schema'], t['table_name'])

        if t['table_name'] == 'Subject':
            uuid_field = 'subject_uuid'
        else:
            uuid_field = [f for f in table.heading.secondary_attributes
                            if '_uuid' in f and 'subject' not in f][0]

        query = table & [{uuid_field: pk} for pk in modified_pks if is_valid_uuid(pk)]

        if query:
            members = t.pop('members')
            update_fields(**t, pks=query.fetch('KEY'), insert_to_table=True)

            if members:
                for m in members:
                    sub_t = getattr(t['real_schema'], m)
                    if sub_t & query:
                        update_fields(t['real_schema'], t['shadow_schema'],
                                      m, (sub_t & query).fetch('KEY'),
                                      insert_to_table=True)


if __name__ == '__main__':

    dj.config['safemode'] = False

deleted_pks, modified_pks = (job.Job & 'job_date="2020-09-03"').fetch1(
    'deleted_keys', 'modified_keys'
)
# delete_entries_from_membership(deleted_pks+modified_pks)
update_entries_from_real_tables(modified_pks)
