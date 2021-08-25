import datajoint as dj
import ibl_pipeline
from ibl_pipeline import update, reference, subject, behavior


schema = dj.schema('ibl_update')


@schema
class DeletionError(dj.Manual):
    definition = """
    -> update.DeletionRecord
    deletion_error_ts=CURRENT_TIMESTAMP : timestamp
    ---
    deletion_error_msg:  varchar(255)
    """


if __name__ == 'main':

    records_for_deletion = update.DeletionRecord & 'deleted=0' & \
                        [{'table': "ibl_pipeline.subject.Subject"}]

    for r in records_for_deletion.fetch('KEY'):

        current_record = records_for_deletion & r

        pk_dict, table_name = current_record.fetch1(
            'pk_dict', 'table')

        table = eval(table_name)

        with dj.config(safemode=False):
            if not len(behavior.TrialSet & pk_dict):
                try:
                    (table & pk_dict).delete()
                    dj.Table._update(current_record, 'deleted', True)
                    print(f'Deleted record {pk_dict}.')

                except BaseException as e:
                    if len(str(e)) > 255:
                        error_msg = str(e)[0:250]
                    else:
                        error_msg = str(e)
                    DeletionError.insert1(
                        dict(**current_record.fetch1(),
                            deletion_error_msg=error_msg))
            else:
                print(f'Skip deleting {pk_dict} because behavior data exists for this record')
