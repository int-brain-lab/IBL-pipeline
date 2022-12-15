# `iblalyx` Docker

A set of containers to run a local Alyx server and connect to a local postgres database.

## Quick Setup

1. Change to the [docker directory](./): `cd ./local-alyx-docker`.

2. Rename `template.env` to `.env`. Set the required environment variables.

3. Run `docker-compose up --detach` ([docker](https://docs.docker.com/get-docker/) and [docker compose](https://docs.docker.com/compose/install/) must be installed).

4. Check if the server is running by going to http://localhost:8000/admin, then sign in using the values defined in the `.env` file.

5. Run the following command to view more ways to interact with Alyx.
   - `docker exec $(docker ps -aqf "name=alyx-apache") alyx --help`

_See below for more details._

## Environment

Information stored in variables and used throughout the services. Some variables may be stored in `.env` files and are purely for use within `docker-compose.yml` (not found as a build `ARG` in the image or `ENV` variable for use in a running container), others can also be stored in a `.env` file and used within the container as environment variables or during the image build process as build arguments, both of which are passed via `docker compose` or `docker run`.

### Required

The following environment variables are required for minimal use. Set them in a `.env` file (see example `template.env`), or specify them manually in either `docker-compose.yml` or when using `docker run`.

- **`PGPASSWORD`**, **`POSTGRES_PASSWORD`**

  - _description_: Sets the database password for the `postgres-13` image running the postgres server, as well as for the `iblalyx` image for use with sudo, settings, and admin db access.
  - _`.env` file_: Set `ALYX_ADMIN_PASS`

- **`POSTGRES_DB`**, **`PGDATABASE`**

  - _description_: Sets the main database name for the `postgres-13` and `iblalyx` images.
  - _`.env` file_: Set `ALYX_DBNAME`

- **`DJANGO_SECRET_KEY`**

  - _description_: Sets `SECRET_KEY` in `settings_secret.py` for the `iblalyx` image.
  - _`.env` file_: Set `DJANGO_SECRET_KEY`

### Suggested

The following environment variables are optional but are suggested to be set manually.

- **`FLATIRON_SERVER_LOGIN`**

  - _description_: Sets `FLATIRON_SERVER_LOGIN`. Used for flatiron access such as downloading database dumps or use with ONE-api.
  - _`.env` file_: Set `FLATIRON_SERVER_LOGIN`

- **`FLATIRON_SERVER_PWD`**

  - _description_: Sets `FLATIRON_SERVER_PWD`. Used for flatiron access such as downloading database dumps or use with ONE-api.
  - _`.env` file_: Set `FLATIRON_SERVER_PWD`

### Optional

These variables are already set elsewhere, such as in the `Dockerfile` or in `docker-compose.yml`, but may be required if building your own image.

- **`ALYX_INSTANCE`**

  - _description_: Sets the `ALYX_INST_TYPE` build arg in the `iblalyx` image.
  - _default_: `local`
  - _`.env` file_: Set `ALYX_INST_TYPE`

- **`POSTGRES_USER`**, **`PGUSER`**

  - _description_: Sets `USER_NAME` in the `iblalyx` image as well as the user for the postgres image.
  - _default_: `ibl_dev`
  - _`.env` file_: Set `ALYX_ADMIN_USER`

- **`PGREADONLY`**

  - _description_: Set `PGREADONLY=on` to configure the `"default"` `DATABASE` settings to be in read-only mode (see [`settings_secret_template.py`](build/settings/settings_secret_template.py)).
  - _default_: `off`
  - _`.env` file_: Set `PGREADONLY`

- **`ALYX_PORT`**

  - _description_: Set a different port for the alyx web server
  - _default_: `8000`
  - _`.env` file_: Set `ALYX_PORT`

## Docker Compose

Create and start the containers using the services specified in [`docker-compose.yml`](docker-compose.yml). The compose file uses a pre-built `iblalyx` image to start the Alyx and postgres services. The pre-built image is based on these default arguments passed during the build process:

- **`ALYX_INST_TYPE`**

  - _default_: `local`
  - _description_: Set's the root path for Alyx source materials, e.g., `/var/www/alyx-local`

- **`ALYX_GITHUB_BRANCH`**

  - _default_: `dev`
  - _description_: The branch to clone from [github.com/cortex-lab/alyx](https://github.com/cortex-lab/alyx)

- **`ALYX_SERVICE_NAME`**

  - _default_: `alyx-apache`
  - _description_: This is is name of the service that is running the postgres database and should be on the same container network.

- **`TIMEZONE`**

  - _default_: `"Europe/Lisbon"`
  - _description_: Sets system environment variable `TZ`.

- **`USER_NAME`**

  - _default_: `ibl_dev`
  - _description_: Name of the superuser managing alyx resources.

- **`USER_UID`**

  - _default_: `1000`
  - _description_: User id for `USER_NAME`. It can be whatever except `0` or `999`.

- **`PY_VER`**

  - _default_: `3.9`
  - _description_: Python version used throughout the image.

Environment variables defined in the image are either derived from these defaults or must be supplied by you when running the container. If you wish to use different build arguments, see the file `docker-compose-build-local.yml` for building a local image with different build arguments defined in a `.env` file.

For an example on defining variables used across different images, see the `template.env` file.

The `alyx-apache` service will likely take a few minutes to initialize the database and load in the fixtures.

## Docker Build and Run

```bash
cd local-alyx-docker/build
PLTARCH=$(uname -m)
GITHUB_USERNAME=iamamutt
docker build \
    --platform=linux/${PLTARCH} \
    --target=iblalyx \
    --tag=ghcr.io/${GITHUB_USERNAME}/dj-iblalyx:latest \
    --build-arg IMAGE_CREATED=2022-11-11T11:11:11Z \
    --build-arg IMAGE_VERSION=v0.0.0 \
    .
```

```bash
docker run \
    --rm -itdu "root:docker" \
    --name iblalyx_local \
    --env-file .env
    --entrypoint bash \
    ghcr.io/${GITHUB_USERNAME}/dj-iblalyx:latest \
    -
```

### Building intermediate stages

For running and debugging intermediate stages before the final target stage.

**Stage**: `micromamba_debian`

```bash
cd local-alyx-docker/build
PLTARCH=$(uname -m)              # target architecture for platform
MSTARG=micromamba_debian         # multi-stage build target name
IMGTAG=iblalyx-alyx-test:v0.0.0  # image tag
DCNAME=alyx-test                 # container name
DCUSER=ubuntu                    # container user
```

```bash
# build
docker build --platform=linux/${PLTARCH?} --target=$MSTARG --tag=$IMGTAG .

# start container
docker run --rm -itdu "$DCUSER:docker" --name $DCNAME $IMGTAG bash

# execute a command to running container as root
DCID=$(docker ps -aqf "name=$DCNAME")
docker exec -u "root:docker" ${DCID?} chown $DCUSER:docker /usr/local/conda-meta/history

# stop container
docker stop $DCNAME
```

**Stage**: `iblalyx`

```bash
MSTARG=iblalyx
IMGTAG=iblalyx-no-web:v0.0.0
DCNAME=iblalyx-no-web
DCUSER=ubuntu
```

Use the same docker commands from above.

**Stage**: `iblalyx-apache`

```bash
MSTARG=iblalyx_apache
IMGTAG=iblalyx-web:v0.0.0
DCNAME=iblalyx-web
DCUSER=ibl_dev
```

```bash
docker run -itdu "$DCUSER:docker" --name $DCNAME $IMGTAG -
DCID=$(docker ps -aqf "name=$DCNAME")
docker exec -u "root:docker" ${DCID?} chown -R $DCUSER:docker /usr/local
```

## Interaction with the database

There are 3 main ways to interact with the database, listed below:

|                    | **Where**   | **Who**    | **Notes**                                                                                                                                                                                                                    |
| ------------------ | ----------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Django Shell**   | server only | admin only | This hits the database directly. It is a very powerful way to do maintenance at scale, with the risks associated. Run the `./manage.py shell` Django command to access the Ipython shell.                                    |
| **Admin Web Page** | web client  | anyone     | Manual way to input data in the database. This is privilegied for users needing to add/amend/correct metadata related to subjects. For the local database, this is accessible here: http://localhost:8000/admin.             |
| **REST**           | web client  | anyone     | Programmatical way to input data, typically by acquisition software using a dedicated Alyx client [ONE](https://github.com/int-brain-lab/ONE) (Python) or [ALyx-matlab](https://github.com/cortex-lab/alyx-matlab) (Matlab). |

### Django

Use the `django` module directly. Requires access to model source code and all settings setup correctly. See [alyx_cfg.py](./build/scripts/alyx_cfg.py) for setting up settings files by passing environment variables and `.env` files as command line arguments.

See [django_connect.py](./test/django_connect.py)

### ONE API

To create an experiment, register data and access it locally, see [one_connect.py](./test/one_connect.py)

We went straight to the point here, which was to create a session and register data, to go further consult the [One documentation](https://int-brain-lab.github.io/ONE/), in the section "Using one in Alyx".

## Alyx bash script

The `alyx` command is located at `/usr/local/bin/alyx` inside the container. It can also be called from the host machine using `docker exec`, for example:

```bash
DCID=$(docker ps -aqf "name=alyx-apache")
docker exec "$DCID" alyx --backup-date=2022-05-01 fetch_and_load_db
```

```bash
docker exec $(docker ps -aqf "name=alyx-apache") alyx --help
```

```
usage: alyx [OPTION]... FUNC/ROUTINE...

Entrypoint for Alyx database and webserver management and configuration.


Functions: standalone operations
--------------------------------

create_db ......... Create a new, empty postgres database if it does not already exist.
                    It will be named from the env variable PGDATABASE='alyxlocal'.
config_settings ... Configure Alyx/Django settings. Some environment variables like
                    PGUSER, PGHOST, PGDATABASE, and PGPASSWORD are required.
config_apache ..... Configure Apache server settings.
update_alyx ....... Make migrations, migrate, load fixtures, set permissions.
fetch_dump ........ Download Alyx database dump from the date set from the env variable
                    BACKUP_DATE or from the option '--dump-url'.
load_db ........... Load data from the sql dump into the postgres 'alyxlocal'
                    database if file '/var/www/alyx-local/shared/local/db_loaded.out'
                    does not already exist.
dump_json ......... Send command to perform a JSON dump of the current database.
                    Database stored at '/var/www/alyx-local/cache/dumps/json'
dump_sql .......... Send command to perform a SQL dump of the current database.
                    Database stored at '/var/www/alyx-local/cache/dumps/sql'
clean_sql_dumps.... Clean up existing SQL dumps in the dump folder.
                    Use with option '--exp-days'.
clean_dls ......... Clean up downloads from cache folder.
                    Use with option '--exp-days'.
reset_alyx ........ Reset 'alyxlocal' to empty. Won't reload database.
start_server ...... Start Alyx web server using port '8000'.
check_server ...... Check if Alyx web server is up and running.
stop_server ....... Stop apache2 server if it is running.


Routines: run several functions in a sequence
---------------------------------------------

init_db ............... Routine that performs all initialization steps to bring up the
                        database 'alyxlocal' by running: create_db,
                        config_settings, config_apache, update_alyx, create_su.
fetch_and_load_db ..... Routine that inserts the latest sql dump into the postgres
                        database 'alyxlocal' by running: fetch_dump, load_db.
fetch_and_reload_db ... Routine that inserts the latest sql dump and resets database
                        'alyxlocal' by running: fetch_dump, load_db --reset.
www ................... Routine that initializes environment and runs the web server
                        by running: init_db, fetch_and_load_db, start_server
www_no_load ........... Routine that initializes environment and runs the web server
                        by running: init_db, start_server
dev ................... Start a process that waits indefinitely. Should be specified at
                        the end of the command.


Options: --option=value | --option
-----------------------

--data-path=SQL_FILE_PATH ... Local SQL dump file path. If the file already exists, this
                              will be used for other operations like loading the dump.
                              If it doesn't exist, it will be used as where to save the
                              SQL dump obtained from the path generated from the dump
                              date stored in BACKUP_DATE.
--backup-date=BACKUP_DATE ... Date used to fetch database dump in YYYY-mm-dd format.
--dump-url=SQL_DUMP_URL ..... Full url of sql dump instead of using BACKUP_DATE to form
                              the url. Example url:
                              https://ibl.flatironinstitute.org/json/2022-05-19_alyxfull.sql.gz
--exp-days=EXPIRES_AFTER .... Number of days for dumps to be considered expired when
                              using the function 'clean_dls'.
                              Default is 6 days.
--force-load ................ Forces deletion of the database loaded file:
                              '/var/www/alyx-local/shared/local/db_loaded.out'
                              Useful for loading the database keeping existing data.

========================================================================================

Default Environment Variables (also available if script is sourced):

  PGDATABASE=alyxlocal
  PGHOST=alyx-postgres
  PGUSER=ibl_dev
  PGPASSWORD=******
  APACHE_CTL_EXISTS=false
  ALYX_INSTANCE=local
  ALYX_SRC_PATH=/var/www/alyx-local
  ALYX_CACHE_DIR=/var/www/alyx-local/cache
  ALYX_DUMP_DIR=/var/www/alyx-local/cache/dumps
  ALYX_PORT=8000
  ALYX_NETWORK=alyx-apache
  BACKUP_DATE=2022-05-19
  SQL_FILE_PATH=/var/www/alyx-local/cache/dumps/sql/2022-05-19_alyxfull.sql.gz

File Status:

  db_loaded: NO
  alyx_server_start_file: NO
  su_token_fixture: NO
  alyx_lock_file: NO


Examples:

 Run several functions in a specific order.

     alyx fetch_dump create_db load_db

 Run the routine for fetching and loading a SQL dump from specific date.

     alyx --backup-date=2021-10-07 fetch_and_reload_db

 Clean existing SQL dumps older than 3 days.

     alyx --exp-days=3 clean_dls

 Source the variables and functions in this script.

     source alyx
     manage_alyx --help
```
