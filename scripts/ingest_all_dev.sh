exec &> log_dev.txt
start=`date +%s`
python delete_shadow_tables_for_updates.py
python ingest_alyx_raw.py "$@"
python ingest_alyx_shadow.py
python ingest_alyx_shadow_membership.py
python delete_real_tables_for_updates.py
python ingest_alyx_real.py
python ingest_behavior.py
python analyses_behavior.py
python create_summary_csv.py
cd ../prelim_analyses/behavioral_snapshots
python behavioral_snapshot.py
python behavioral_overview_perlab.py
end=`date +%s`
runtime=$((end-start))
