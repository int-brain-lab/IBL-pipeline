#! /usr/bin/env python3

import os
import sys
import logging


from code import interact

# BOOKMARK: ensure loading
from ibl import reference
from ibl import subject
from ibl import acquisition
from ibl import behavior
from ibl import ephys


log = logging.getLogger(__name__)
__all__ = [reference, subject, acquisition, behavior, ephys]


def usage_exit():
    print("usage: {p} [{c}]"
          .format(p=os.path.basename(sys.argv[0]),
                  c='|'.join(list(actions.keys()))))
    sys.exit(0)


def logsetup(*args):
    logging.basicConfig(level=logging.ERROR)
    log.setLevel(logging.DEBUG)
    logging.getLogger('ibl').setLevel(logging.DEBUG)
    logging.getLogger('ibl.ingest').setLevel(logging.DEBUG)


def shell(*args):
    interact('ibl shell.\n\nschema modules:\n\n  - {m}\n'
             .format(m='\n  - '.join(
                 '.'.join(m.__name__.split('.')[1:]) for m in __all__)),
             local=globals())


def ingest(*args):
    # local import so db is only created created/accessed if/when ingesting
    from ibl.ingest import reference as ingest_reference
    from ibl.ingest import subject as ingest_subject
    from ibl.ingest import acquisition as ingest_acquisition
    for mod in [ingest_reference, ingest_subject, ingest_acquisition]:
        pass


actions = {
    'shell': shell,
    'ingest': ingest,
}


if __name__ == '__main__':

    if len(sys.argv) < 2 or sys.argv[1] not in actions:
        usage_exit()

    logsetup()

    action = sys.argv[1]
    actions[action](sys.argv[2:])
