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
