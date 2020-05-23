import datajoint as dj
import ibl_pipeline
from ibl_pipeline import update, reference, subject
from uuid import UUID

schema = dj.schema('ibl_update')


@schema
class UpdateError(dj.Manual):
    definition = """
    -> update.UpdateRecord
    update_action_ts=CURRENT_TIMESTAMP  : timestamp   # time stamp of the update error
    ---
    update_error_msg:     varchar(255)
    """


def get_ts_attr(table):
    return [attr for attr in table.heading.secondary_attributes if '_ts' in attr][0]

# get the unique records
records_for_updating = dj.U('table', 'attribute', 'pk_hash') & \
                       (update.UpdateRecord & {'updated': False} &
                        [{'table': 'ibl_pipeline.subject.Subject'}])

updated_errors = []
for r in records_for_updating.fetch('KEY'):

    current_record = records_for_updating & r

    q = current_record.aggr(
        (update.UpdateRecord & {'updated': False}), update_ts='max(update_ts)')
    last_record = update.UpdateRecord & q

    pk_dict, table, attribute, updated_value, original_value, update_ts = last_record.fetch1(
        'pk_dict', 'table', 'attribute', 'updated_value', 'original_value', 'update_ts')

    key = last_record.fetch1('KEY')

    table = eval(table)

    try:
        # update the current record
        dj.Table._update(table & pk_dict, attribute, updated_value)

        # update the updated status
        dj.Table._update(last_record, 'updated', True)

        # update the timestamp of the field in the original table
        attr_ts = get_ts_attr(table)
        dj.Table._update(table & pk_dict, attr_ts, update_ts)

        print(f'Updated {pk_dict} field "{attribute}" from {original_value} to {updated_value}')

    except BaseException as e:
        if len(str(e)) > 255:
            error_msg = str(e)[0:250]
        else:
            error_msg = str(e)
        print(len(last_record))
        UpdateError.insert1(
            dict(**key,
                 update_error_msg=error_msg))
        print(f'Fail to update {pk_dict} field "{attribute}" from {original_value} to {updated_value}')
