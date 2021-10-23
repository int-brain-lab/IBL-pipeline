# Containerized Alyx Database

This is a stanadalone image that serves as a middleman between the postgres service and the service running the ONE-api.

## Example installation

1. Download the repository

```bash
mkdir -p ~/docker_alyx
cd ~/docker_alyx
git clone -b new-ingestion https://github.com/iamamutt/IBL-pipeline.git
cd IBL-pipeline/docker/ibl/alyx 
```

2. Add your credentials

```bash
touch .env
cat template.env >> .env
```

Open file `.env` and edit the values manually.

3. Build and start the containers

```bash
docker-compose up --build --detach pgserv adminer alyx
ctid="`docker ps -a -q -f name=alyx_alyx`" 
docker exec -t $ctid alyx initb 
docker image prune
```

**NOTE:** If updating container, do these steps before step 1 above.

```bash
cd ~/docker_alyx/docker/ibl/alyx
docker-compose down 
cd ~/docker_alyx/IBL-pipeline
git checkout new-ingestion
git pull
docker system prune --volumes
```

## Reproduce JSON dump daily ingestion routine

Save below as the script `~/run_ingest_local.sh`, then `chmod +x ~/run_ingest_local.sh`

```bash
#! /bin/sh

err_exit() {
	echo "#! Error: $*"
	exit 1
}

echo "#! running `basename $0` at `date`"
echo $(docker ps -a)
cd /home/ubuntu/IBL-pipeline/data

dl_date=$(date -u +'%Y-%m-%d')
dump_file="/int-brain-lab/data/alyx/dumps/sql/alyxfull.sql.gz"
dump_url="http://ibl.flatironinstitute.org/json/${dl_date}_alyxfull.sql.gz"

echo "#! fetch at `date`"
alyx_cid="`docker ps -a -q -f name=alyx_alyx`"
[ -z "$alyx_cid" ] && err_exit "cannot find alyx container"
docker exec -t $alyx_cid alyx --dump_file="$dump_file" --dump_url="$dump_url" reloaddb dumpjson
set -e
docker cp ${alyx_cid}:/int-brain-lab/data/alyx/dumps/json/alyx_full.json alyx_full.json
[ -f "alyx_full.json" ] || err_exit "no new dump data alyx_full.json found"
# move last json dump to *.last
[ -f "alyxfull.json" ] && mv -f alyxfull.json alyxfull.json.last
# move new dump to current filename
[ -f "alyx_full.json" ] && mv -f alyx_full.json alyxfull.json
set +e

echo "#! ingest at `date`"
ingest_cid="`docker ps -q -f name=ibl-pipeline_production`"
[ -z "$ingest_cid" ] && err_exit "cannot find ibl-pipeline_production container"
docker exec -t $ingest_cid /bin/sh -c "cd /src/IBL-pipeline/scripts; QT_DEBUG_PLUGINS=0 ipython ./ingest_increment.py"
echo "#! ephys at `date`"
docker exec -t $ingest_cid /bin/bash -c "cd /src/IBL-pipeline/ibl_pipeline/process; QT_DEBUG_PLUGINS=0 python3 populate_ephys.py"

echo "#! cleanup at `date`"
du -h --max-depth=1 | sort -h
rm -vf alyx_full.json
docker exec -t $alyx_cid alyx --dump_exp=0 cleandumps
find ~/IBL-pipeline/data/FlatIron -mindepth 1 ! -type d -not -name histology -printf '%s %p\n'
find ~/IBL-pipeline/data/FlatIron -mindepth 1 ! -type d -not -name histology -delete
find /tmp/datajoint-ingest*.log -type f -mtime +6
find /tmp/datajoint-ingest*.log -type f -mtime +6 -delete
find ~/IBL-pipeline/data/daily_increments -type f -mtime +6
find ~/IBL-pipeline/data/daily_increments -type f -mtime +6 -delete
echo "#! script finished at `date`"
```

Run the script with:

```bash
~/run_ingest_local.sh >> "/tmp/datajoint-ingest_$(date +'%Y-%m-%d_%H').log" 2>&1
```

...or add that to your cron jobs.
