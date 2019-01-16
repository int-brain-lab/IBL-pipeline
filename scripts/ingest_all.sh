python ingest_alyx_raw.py "$@"
python ingest_alyx_shadow.py
python ingest_alyx_shadow_membership.py
python ingest_alyx_real.py
python ingest_behavior.py
cd ../behavioral_snapshots
python behavioral_snapshot.py
python behavioral_overview_perlab.py
