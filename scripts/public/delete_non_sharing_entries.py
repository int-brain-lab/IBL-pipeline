"""
This script deletes the entries that are not shared in the public release of Jan 2020
"""

from ibl_pipeline import acquisition, action, data, public, reference, subject

# delete all subjects that are not in the list
(subject.Subject - public.PublicSubjectUuid).delete()

# delete all sessions that are not in the list
(acquisition.Session & 'session_start_time>"2019-12-01"').delete()
