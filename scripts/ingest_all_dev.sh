start=`date +%s`
python delete_shadow_tables_for_updates.py
python ingest_alyx_raw.py "$@"
python ingest_alyx_shadow.py
python ingest_alyx_shadow_membership.py
python delete_real_tables_for_updates.py
python ingest_alyx_real.py
python behavior_ingest_analyses.py
end=`date +%s`
runtime=$((end-start))
