date
echo "Deleting alyx shadow tables for updates..."
python delete_shadow_tables_for_updates.py
date
echo "Ingesting alyx raw..."
python ingest_alyx_raw.py "$@"
date
echo "Ingesting alyx shadow tables..."
python ingest_alyx_shadow.py
date
echo "Ingesting alyx shaodow data tables..."
python ingest_data_tables.py
date
echo "Ingesting alyx shadow membership tables..."
python ingest_alyx_shadow_membership.py
date
echo "Deleting real tables for updates..."
python delete_real_tables_for_updates.py
date
echo "Copying shadow tables to real tables..."
python ingest_alyx_real.py
date
echo "Auto updating subject fields..."
python auto_update_subject_fields.py
date
echo "Populating behavior tables..."
python ingest_behavior.py
date
echo "Populating behavior analyses tables..."
python analyses_behavior.py
date
echo "Populating behavior plotting tables..."
python plotting_behavior.py
date
