import datajoint as dj
from ibl_pipeline import uptdate, reference, subject

schema = dj.schema('ibl_update')


@schema
class UpdateError(dj.Manual):
    definition = """
    update_action_ts=CURRENT_TIMESTAMP  : timestamp   # time stamp of the
    ---
    error_update_records=null           : longblob    # list of updated records with errors
    """


def get_ts_attr(table):
    return [attr for attr in table.heading.secondary_attributes if '_ts' in attr][0]

# get the unique records
records_for_updating = dj.U('table', 'attribute', 'pk_hash') & update.UpdateRecord & \
                       'table in ("ibl_pipeline.subject.Subject")'

updated_errors = []
for r in records_for_updating:

    current_record = records_for_updating & r
    last_record = update.UpdateRecord & current_record.aggr(
        records_for_updating & 'update=0', updated_ts='max(update_ts)')

    pk_dict, table, attribute, updated_value, original_value = last_record.fetch1(
        'pk_dict', 'table', 'attribute', 'updated_value', 'original_value')

    table = eval(table)

    try:
        # update the current record
        dj.Table._update(table & pk_dict, attribute, updated_value)

        # update the updated status
        dj.Table._update(last_record, 'updated', 1)

        # update the timestamp of the field in the original table
        attr_ts = get_ts_attr(table)
        dj.Table._update(table & pk_dict, attr_ts, last_record.fetch1('update_ts'))

        print(f'Updated {pk_dict} field "{attribute}" from {original_value} to {updated_value}')

    except:
        updated_errors.append(last_record.fetch1('KEY'))
        print(f'Fail to update {pk_dict} field "{attribute}" from {original_value} to {updated_value}')

UpdateError.insert1(dict(error_update_records=updated_errors))
