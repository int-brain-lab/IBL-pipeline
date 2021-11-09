# Populate IBL DataJoint Tables from Alyx/Flatiron

A set of containers to run a local Alyx server and run the DataJoint ingestion routines for populating the IBL DataJoint tables.

## Initial setup

From the IBL-pipeline repo directory, navigate to the docker datajoint directory.

```bash
cd docker/datajoint
```

Setup the required environment variables to connect to Alyx and DataJoint by using the `template.env` file. Fill out the variables in `.env` copied over from `template.env`.

```bash
touch .env
cat template.env >> .env
```

Create and start the containers using the services specified in `docker-compose.yml`.

```bash
docker-compose up --detach
```

The `alyx_db_server` container will likely take a few minutes to download the public database and load in the sql dump.

You can set a cron job to periodically download the latest sql dump and load it into the database. For example, create a script called `alyxreload.sh` with the following content:

```bash
#! /bin/sh
echo "#! Script `basename $0` started at `date`"

ALYX_CONTAINER=alyx_db_server
SQL_DUMP_EXPIRES=4

err_exit() {
	echo "#! Error: $*"
	exit 1
}

ALYX_CID="`docker ps -a -q -f name=$ALYX_CONTAINER`"
[ -z "$ALYX_CID" ] && err_exit "Cannot find alyx container."

echo "#! Fetch started at `date`"
docker exec -t $ALYX_CID alyx reloaddb 

echo "#! Cleanup started at `date`"
docker exec -t $ALYX_CID alyx --dump_exp=$SQL_DUMP_EXPIRES cleandls

echo "#! Script `basename $0` finished at `date`"
```

Use `crontab -e` to add the last line to your cron jobs to run the above script everyday at 00:45. 

```
# %M=min (0-59)
# %H=hour (0-23)
# %d=day of month (1-31)
# %m=month (1-12)
# %w=day of week (0-6, sun=0)
# %M %H %d %m %w command
45 0 * * * /home/user/alyxreload.sh >> "/tmp/alyxreload_$(date +'\%Y-\%m-\%d_\%H').log" 2>&1
```
