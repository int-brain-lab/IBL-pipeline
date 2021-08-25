python drop_alyx_raw.py
python ingest_alyx_raw.py "$@"
python ingest_alyx_shadow_updates.py
python ingest_alyx_shadow_membership_updates.py

