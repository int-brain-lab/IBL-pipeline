"""

ibl.ingest

This package contains 'shadowed' copies of main tables for external data load
most classes here will be defined using
<downstream_module>.RealClass.definition;

Only if some merging/disambiguation will definitions be augmented/modified
locally in some way with additional attributes and/or tables to facillitate the
difference. These differences should still result in tables compatbile with
data copying via insert from select (e.g: Foo.insert(Bar.fetch()))

NOTE:

Since downstream modules involve cross-module definitions, those modules should
be imported as 'ds_module' in order to prevent the possibility of accidental
linkages to downstream tables in the upstream schema.

For example, in the scenario:

  - foo.py defines Foo
  - bar.py defines Bar referencing foo.Foo

  - ingest.bar imports .. foo (for some other reason than foo.Foo)
  - ingest.bar imports .. bar (to get foo.Foo schema string)
  - ingest.bar.Bar.definition = bar.Bar.definition

Setting ingest.bar.Bar.definition = bar.Bar.definition creates an accidental
link to downstream foo.Foo table because 'bar' points to the downstream
module. If foo/bar had been imported as ds_foo/ds_bar instead, the table
definition syntax would not properly resolve any 'foo' in the scope of
ingest.bar and the definition would fail, also failing to create the bad link.



In this scheme, the 'correct' implementation would instead be:

  - foo.py defines Foo
  - bar.py defines Bar referencing foo.Foo

  - ingest.bar imports .. foo as ds_foo (for some other reason than foo.Foo)
  - ingest.bar imports .. bar as ds_bar (to get foo.Foo schema string)
  - ingest.bar imports . foo (to get ingest.foo.Foo)
  - ingest.bar.Bar.definition = bar.Bar.definition

Now, ingest.bar.Bar is able to use bar.Bar.definition, but the definition
of ingest.bar.Bar is resolved within the scope of ingest.bar as pointing to
ingest.foo.Foo, creating the proper link to the ingest related table.

While this should not happen in the current architecture, following the pattern
outlined here should prevent it in general and so is a good 'safe practice' to
use for the ingest modules.
"""


import datajoint as dj

from ibl_pipeline import mode
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline.utils import get_logger

if mode == "test":
    dj.config["database.prefix"] = "test_"

logger = get_logger(__name__)


def get_raw_field(key, field, multiple_entries=False, model=None):
    if model:
        query = (
            alyxraw.AlyxRaw.Field
            & (alyxraw.AlyxRaw & 'model="{}"'.format(model))
            & key
            & 'fname="{}"'.format(field)
        )
    else:
        query = alyxraw.AlyxRaw.Field & key & 'fname="{}"'.format(field)

    if not query:
        raise AlyxKeyError(f'No "{field}" field in AlyxRaw.Field for key: {key}')

    return (
        query.fetch1("fvalue")
        if not multiple_entries and len(query)
        else query.fetch("fvalue")
    )


class QueryBuffer(object):
    """
    QueryBuffer: a utility class to help managed chunked inserts
    Currently requires records do not have prerequisites.
    """

    def __init__(self, rel, verbose=False):
        self._rel = rel
        self._queue = []
        self._delete_queue = []
        self.fetched_results = []
        self.verbose = verbose

    def add_to_queue1(self, r):
        self._queue.append(r)

    def add_to_queue(self, recs):
        self._queue.extend(recs)

    def flush_insert(self, chunksz=None, **kwargs):
        """
        flush the buffer
        XXX: ignore_extra_fields na, requires .insert() support
        """
        qlen = len(self._queue)
        if not qlen:
            return

        chunksz = chunksz or qlen
        failed_insertions = []
        while qlen >= chunksz:
            entries = self._queue[:chunksz]
            del self._queue[:chunksz]
            try:
                self._rel.insert(entries, **kwargs)
            except Exception as e:
                logger.info(
                    "error in flush-insert: {}"
                    " - Trying ingestion one by one ({} records)".format(
                        e, len(entries)
                    )
                )
                for entry in entries:
                    try:
                        self._rel.insert1(entry, **kwargs)
                    except Exception as e:
                        failed_insertions.append(entry)
                        logger.error("error in flush-insert: {}".format(e))
            if self.verbose:
                logger.log(
                    0,
                    "Inserted {}/{} raw field tuples".format(
                        chunksz - len(failed_insertions), chunksz
                    ),
                )

            del entries
            qlen = len(self._queue)  # new queue size for the next loop-iteration

        return failed_insertions

    def flush_delete(self, chunksz=1, quick=True):
        """
        flush the delete
        """

        qlen = len(self._queue)
        if qlen > 0 and qlen % chunksz == 0:
            try:
                with dj.config(safemode=False):
                    if quick:
                        (self._rel & self._queue).delete_quick()
                    else:
                        (self._rel & self._queue).delete()
            except Exception as e:
                print("error in flush delete: {}, trying deletion one by one".format(e))
                for t in self._queue:
                    try:
                        with dj.config(safemode=False):
                            if quick:
                                (self._rel & t).delete_quick()
                            else:
                                (self._rel & t).delete()

                    except Exception as e:
                        print("error in flush delete: {}".format(e))
            self._queue.clear()
            return qlen
        else:
            return 0

    def flush_fetch(self, field, chunksz=1):
        """
        flush the fetch
        """
        qlen = len(self._queue)
        if qlen > 0 and qlen % chunksz == 0:
            try:
                self.fetched_results.extend((self._rel & self._queue).fetch(field))
            except Exception as e:
                print("error in flush fetch: {}, trying fetch one by one".format(e))
                for t in self._queue:
                    try:
                        self.fetched_results.append(
                            (self._rel & self._queue).fetch1(field)
                        )
                    except Exception as e:
                        print("error in flush fetch: {}".format(e))
            self._queue.clear()
            return qlen
        else:
            return 0


def populate_batch(t, chunksz=1000, verbose=True):

    keys = (t.key_source - t.proj()).fetch("KEY")
    table = QueryBuffer(t)
    for key in keys:
        entry = t.create_entry(key)
        if entry:
            table.add_to_queue1(entry)

        if (
            table.flush_insert(
                skip_duplicates=True, allow_direct_insert=True, chunksz=chunksz
            )
            and verbose
        ):
            print(f"Inserted {chunksz} {t.__name__} tuples.")

    if table.flush_insert(skip_duplicates=True, allow_direct_insert=True) and verbose:
        print(f"Inserted all remaining {t.__name__} tuples.")


class ShadowIngestionError(Exception):
    """Raise when ingestion failed for any shadow table"""

    def __init__(self, msg=None):
        super().__init__("ShadowIngestionError: \n{}".format(msg))

    pass


class AlyxKeyError(Exception):
    """Raise when KeyError encountered when accessing Alyx fields"""

    def __init__(self, msg=None):
        super().__init__("AlyxKeyError: \n{}".format(msg))

    pass
