"""
functions to compare contents in shadow tables and real tables.
"""
import datajoint as dj
from ibl_pipeline import reference, subject, acquisition
from ibl_pipeline import update
from uuid import UUID


def show(tablepairs, comment=''):
    print('# {} table contents'.format(comment))
    for p in tablepairs:
        print(p)
        for t in tablepairs[p]:
            print(t)
            print(t())


def push(tablenames, tablepairs):
    try:
        print('# pushing data')
        for tname in tablenames:
            source_tbl, dest_tbl = tablepairs[tname]
            dest_tbl.insert(source_tbl() - dest_tbl().proj())
    except Exception as e:
        print('# push error: {e}'.format(e=e))


def get_user(key):
    if len(acquisition.SessionUser & key) == 1:
        user = (acquisition.SessionUser & key).fetch1(
            'user_name')
    elif len(subject.SubjectUser & key) == 1:
        user = (subject.SubjectUser & key).fetch1(
            'responsible_user')
    elif len(reference.LabMember & key) == 1:
        user = (reference.LabMember & key).fetch1(
            'user_name')
    else:
        user = None
    return user


def diff(tablenames, tablepairs):
    # tablepairs [shadow, real]
    for t in tablenames:
        ndiffs = 0
        ndels = 0
        shadow, real = tablepairs[t]

        # only detect deleted entries in the shadow table
        for deleted_key in (real - shadow.proj(*real.primary_key)).fetch('KEY'):

            deleted_entry = (real & deleted_key).fetch1()
            deleted_record = dict(
                table=real.__module__+'.'+real.__name__,
                pk_hash=UUID(dj.hash.key_hash(deleted_key)),
                original_ts=deleted_entry[[key for key in deleted_entry.keys() if '_ts' in key][0]],
                pk_dict=deleted_key,
                deletion_narrative='{} only in {} - record deleted?'.format(
                    deleted_key, real),
            )

            user = get_user(deleted_key)
            if user:
                email = \
                    (reference.LabMember &
                     'user_name="{}"'.format(user)).fetch1(
                         'email'
                     )
                deleted_record.update(
                    responsible_user=user,
                    user_email=email
                )

            update.DeletionRecord.insert1(deleted_record, skip_duplicates=True)
            ndels += 1

        # detect updates in common records of shadow and real tables
        common_records = (real.proj() & shadow.proj(*real.primary_key))
        kstr = ', '.join(real.primary_key)
        shadow_records = (shadow & common_records).fetch(
            order_by=kstr, as_dict=True)
        real_records = (real & common_records.proj()).fetch(
            order_by=kstr, as_dict=True)
        real_keys = (real & common_records.proj()).fetch('KEY', order_by=kstr)

        for shadow_record, real_record, pk in \
                zip(shadow_records, real_records, real_keys):

            for attr in shadow_record:
                shadow_value = shadow_record[attr]
                real_value = real_record[attr]

                if shadow_value != real_value and \
                        (isinstance(shadow_value, str) and
                            '_ts' not in shadow_value):

                    update_record = dict(
                        table=real.__module__+'.'+real.__name__,
                        attribute=attr,
                        pk_hash=UUID(dj.hash.key_hash(pk)),
                        original_ts=real_record[[key for key in real_record.keys() if '_ts' in key][0]],
                        update_ts=shadow_record[[key for key in shadow_record.keys() if '_ts' in key][0]],
                        pk_dict=pk,
                        original_value=real_value,
                        updated_value=shadow_value,
                        update_narrative='{t}.{a}: {s} != {d}'.format(
                            t=t, a=attr, s=shadow_value, d=real_value)
                    )
                    user = get_user(pk)
                    if user:
                        update_record.update(
                            responsible_user=user,
                            user_email=email
                        )
                    update.UpdateRecord.insert1(update_record, skip_duplicates=True)
                    ndiffs += 1

        print('# {} total deleted records in table {}.'.format(ndels, t))
        print('# {} total differences in table {}.'.format(ndiffs, t))


def drop(schemas):
    for s in schemas:
        s.schema.drop(force=True)
