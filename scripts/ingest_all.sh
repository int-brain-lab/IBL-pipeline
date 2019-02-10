python ingest_alyx_raw.py "$@"
python delete_tables_for_updates.py
python ingest_alyx_shadow.py
python ingest_alyx_shadow_membership.py
python ingest_alyx_real.py
python ingest_behavior.py
cd ../prelim_analyses/behavioral_snapshots
python behavioral_snapshot.py
python behavioral_overview_perlab.py
