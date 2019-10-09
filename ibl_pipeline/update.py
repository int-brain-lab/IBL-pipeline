'''
schema for update records
'''
import datajoint as dj

schema = dj.schema('ibl_update')


@schema
class UpdateRecord(dj.Manual):
    definition = """
    table:              varchar(64)
    attribute:          varchar(64)
    pk_hash:            uuid                # hash of the primary key
    original_ts:        timestamp
    update_ts:          timestamp
    ---
    original_value=null:blob
    updated_value=null: blob
    update_narrative=null: varchar(2047)   # narrative of the change
    pk_dict:            longblob
    record_ts=CURRENT_TIMESTAMP :   timestamp
    responsible_user='alyx':   varchar(255)
    user_email='alyx@internationalbrainlab.org':         varchar(128)
    notified=0:         boolean
    updated=0:          boolean
    """


@schema
class DeletionRecord(dj.Manual):
    definition = """
    table:              varchar(64)
    pk_hash:            uuid                 # hash of the primary key
    original_ts:        timestamp
    ---
    pk_dict:            longblob
    record_ts=CURRENT_TIMESTAMP :   timestamp
    deletion_narrative=null: varchar(2047)
    responsible_user='alyx': varchar(255)
    user_email='alyx@internationalbrainlab.org':         varchar(128)
    notified=0:         boolean
    deleted=0:          boolean
    """
