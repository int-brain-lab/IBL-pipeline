date
echo "Ingesting alyx raw..."
python ingest_alyx_raw_dbtest.py
date
echo "Ingesting alyx shadow tables..."
python ingest_alyx_shadow.py
date
echo "Ingesting alyx shadow membership tables..."
python ingest_alyx_shadow_membership.py
date
echo "Copying shadow tables to real tables..."
python ingest_alyx_real.py
date
