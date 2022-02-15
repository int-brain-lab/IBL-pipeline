# ! /bin/bash
# docker exec -t $(docker ps -q -f name=ibl-pipeline_production) /src/IBL-pipeline/scripts/ingest_test.sh
exec &> /tmp/log_dev.txt
start=`date +%s`
cd /src/IBL-pipeline/scripts
echo "Running delete_shadow_tables_for_updates"
ipython delete_shadow_tables_for_updates.py

echo "Running ingest_alyx_raw"
ipython ingest_alyx_raw.py "$@"

echo "Running ingest_alyx_shadow"
ipython ingest_alyx_shadow.py

echo "Running ingest_alyx_shadow_membership"
ipython ingest_alyx_shadow_membership.py

echo "Running delete_real_tables_for_updates"
ipython delete_real_tables_for_updates.py

echo "Running ingest_alyx_real"
ipython ingest_alyx_real.py

echo "Running ingest_behavior"
ipython ingest_behavior.py

echo "Running analyses_behavior"
ipython analyses_behavior.py

echo "Running create_summary_csv"
ipython create_summary_csv.py

# cd ../prelim_analyses/behavioral_snapshots
# ipython behavioral_snapshot.py
# ipython behavioral_overview_perlab.py
end=`date +%s`
runtime=$((end-start))
