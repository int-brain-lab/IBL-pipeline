# IBL pipeline schemas

Alyx-corresponding schemas, including, `reference`, `subject`, `action`, `acquisition`, and `data`

![Alyx_corresponding erd](images/alyx_erd.png)

Schema of `ephys`
![Ephys erd](images/ephys_erd.png)

Schema of `behavior`
![Behavior erd](images/behavior_erd.png)



# Instructions to ingest Alyx data into local database

To run an local instance of database in the background, run the docker-compose command as follows:

```bash
docker-compose -f docker-compose-local.yml up -d
```

This will create a docker container with a local database inside. To access the docker from the terminal, first get the docker container ID with `docker ps`, then run:

```bash
docker exec -it CONTAINER_ID /bin/bash
```

Now we are in the docker, and run the bash script for the ingestion:

```
bash /src/ibl-pipeline/scripts/ingest_alyx.sh ../data/alyx_dump/2018-10-30_alyxfull.json
```

Make sure that the json file is in the correct directory as shown above.

# 

# Instructions to ingest Alyx data into Amazon RDS

To insert Alyx data into the remote Amazon RDS, create a .env file in the same directory of your `docker-compose.yml`. Here are the contents in the .env file:

```bash
DJ_HOST=datajoint-rds.cyuksi65nrdq.us-east-1.rds.amazonaws.com
DJ_USER=YOUR_USERNAME
DJ_PASS=YOUR_PASSWORD
```

Now run the docker-compose as follows, it will by default run through the file `docker-compose.yml`

```bash
docker-compose -f up -d
```

This will create a docker container and link to the remote Amazon RDS. Then follow the same instruction of ingestion to the local database.