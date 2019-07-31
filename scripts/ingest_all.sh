python delete_shadow_tables_for_updates.py
python ingest_alyx_raw.py "$@"
python ingest_alyx_shadow.py
python ingest_alyx_shadow_membership.py
python delete_real_tables_for_updates.py
python ingest_alyx_real.py
python ingest_behavior.py
python analyses_behavior.py
python create_summary_csv.py
python compute_latest_date.py
python plotting_behavior.py
python insert_update_subject_last_date.py
python populate_daily_summary.py
cd ../prelim_analyses/behavioral_snapshots
python behavioral_snapshot.py
python behavioral_overview_perlab.py
