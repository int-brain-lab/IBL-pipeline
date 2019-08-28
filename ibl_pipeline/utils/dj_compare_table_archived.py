"""
functions to compare contents in shadow tables and real tables.
"""
import logging
import datajoint as dj

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
file_handler = logging.FileHandler('table-diff.log')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


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


def diff(tablenames, tablepairs):
    ndiff = 0
    for t in tablenames:
        a, b = tablepairs[t]

        for i in ((a - b.proj()).fetch('KEY')):
            logger.info('# {} only in {} - record deleted?'.format(i, a))

        for i in ((b - a.proj()).fetch('KEY')):
            logger.info('# {} only in {} - record deleted?'.format(i, b))

        common = (a & b.proj(*a.primary_key))
        kstr = ', '.join(a.primary_key)
        srcrecs = (a & common.proj()).fetch(order_by=kstr, as_dict=True)
        dstrecs = (b & common.proj()).fetch(order_by=kstr, as_dict=True)

        for srce, dste in zip(srcrecs, dstrecs):
            for attr in srce:
                srcv = srce[attr]
                dstv = dste[attr]
                if srcv != dstv:
                    print('# {t}.{a}: {s} != {d}'.format(
                        t=t, a=attr, s=srcv, d=dstv))
                    ndiff += 1

        logger.info('# {} total differences.'.format(ndiff))



def drop(schemas):
    for s in schemas:
        s.schema.drop(force=True)