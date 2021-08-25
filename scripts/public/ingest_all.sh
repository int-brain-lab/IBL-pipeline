#python delete_shadow_tables_for_updates.py
# at the beginning, remember to drop the columns ['first_name', 'last_name', 'password', 'email']
python ingest_alyx_raw.py "$@"
python ingest_alyx_shadow.py
python ingest_data_tables.py
python ingest_alyx_shadow_membership.py
python ingest_alyx_real.py
# python ../ingest_behavior.py
# python ../analyses_behavior.py
# python ../compute_latest_date.py
# python ../plotting_behavior.py
# python ../insert_update_subject_last_date.py
# python ../populate_daily_summary.py
