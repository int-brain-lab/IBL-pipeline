# Populate IBL DataJoint Tables from Alyx/Flatiron

A set of containers to run a local Alyx server and run the DataJoint ingestion routines for populating the IBL DataJoint tables.

## Initial setup

After cloning, navigate to the IBL-pipeline repository directory (this is one directory back from this README file).

```bash
cd IBL-pipeline
```

Setup the required environment variables to connect to Alyx and DataJoint by using the `template.env` file. The `.env` should be at the root of the repository content directory. Fill out the variables in `.env` copied over from `template.env`.

```bash
touch .env
cat docker/template.env >> .env
```

Create and start the containers using the services specified in [`docker-compose.yml`](docker-compose.yml).

```bash
docker/docker-compose up --detach
```

The `alyx` service will likely take a few minutes to initialize the database and load in the latest sql dump.

You can set a cron job to periodically download the latest sql dump and load it into the database. For example, create a script called `reload_alyx` with the following content:

```bash
#! /bin/bash

XSH_SRC=${BASH_SOURCE[0]:-${(%):-%x}}
script_dir=$(cd "$(dirname "${XSH_SRC}")" &>/dev/null && pwd)
script_file=$(basename "${XSH_SRC}")

echo "#>> Script $script_file started at $(date +'%Z %Y-%m-%d %H:%M:%S')"

ALYX_CONTAINER_NAME=${1:-alyx_alyx}
POPULATE_CONTAINER_NAME=${2:-alyx_ingest_1}

SQL_DUMP_EXPIRES=3

err_exit() {
	set -e
	echo "#! Error: $*" >&2
	return 1
}

ALYX_CID="$(docker ps -a -q --no-trunc -f name=$ALYX_CONTAINER_NAME)"
echo "# INFO: Alyx container name: $ALYX_CONTAINER_NAME"
echo "# INFO: Alyx container id: $ALYX_CID"
[ -z "$ALYX_CID" ] && err_exit "Cannot find alyx container."

INGEST_CID="$(docker ps -a -q --no-trunc -f name=$POPULATE_CONTAINER_NAME)"
echo "# INFO: Populate/Ingest container name: $POPULATE_CONTAINER_NAME"
echo "# INFO: Populate/Ingest container id: $INGEST_CID"
[ -z "$INGEST_CID" ] && err_exit "Cannot find ingestion container."

echo "#> Ingestion jobs terminate started at $(date +'%Z %Y-%m-%d %H:%M:%S')"
docker exec -t $INGEST_CID ingest terminate
sleep 15

echo "#> Database reload started at $(date +'%Z %Y-%m-%d %H:%M:%S')"
docker exec -t $ALYX_CID alyx fetch_and_reload_db

echo "#> Cleanup started at $(date +'%Z %Y-%m-%d %H:%M:%S')"
docker exec -t $ALYX_CID alyx --dump_exp=$SQL_DUMP_EXPIRES clean_dls
find "${script_dir}/logs/${script_file}_"*.log -type f -mtime +6 -delete 2>/dev/null

echo "#<< Script $script_file finished at $(date +'%Z %Y-%m-%d %H:%M:%S')"
```

Use `crontab -e` to add the last line to your cron jobs to run the above script everyday at 00:45. 

```bash
# Edit this file to introduce tasks to be run by cron.
#
# Each task to run has to be defined through a single line
# indicating with different fields when the task will be run
# and what command to run for the task
#
# To define the time you can provide concrete values for
# minute (m), hour (h), day of month (dom), month (mon),
# and day of week (dow) or use '*' in these fields (for 'any').
#
# Notice that tasks will be started based on the cron's system
# daemon's notion of time and timezones.
#
# Output of the crontab jobs (including errors) is sent through
# email to the user the crontab file belongs to (unless redirected).
#
# For example, you can run a backup of all your user accounts
# at 5 a.m every week with:
# 0 5 * * 1 tar -zcf /var/backups/home.tgz /home/
#
# For more information see the manual pages of crontab(5) and cron(8)
#
# %M=min (0-59)
# %H=hour (0-23)
# %d=day of month (1-31)
# %m=month (1-12)
# %w=day of week (0-6, sun=0)
# %M %H %d %m %w command
45 0 * * * /home/ubuntu/docker_ingest/scripts/reload_alyx >>"/home/ubuntu/docker_ingest/scripts/logs/reload_alyx_$(date +'\%Y-\%m-\%d_\%H_\%M').log" 2>&1
```
