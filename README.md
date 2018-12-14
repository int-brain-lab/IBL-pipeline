# IBL pipeline schemas

Alyx-corresponding schemas, including, `referenall_erd.save('/images/all_erd.png')ce`, `subject`, `action`, `acquisition`, and `data`

![Alyx_corresponding erd](images/alyx_erd.png)

Schema of `ephys`
![Ephys erd](images/ephys_erd.png)

Schema of `behavior`
![Behavior erd](images/behavior_erd.png)

# Instructions for connecting to the IBL pipeline

1. Email austin@vathes.com for a database username.

2. Install Docker (https://www.docker.com/). Linux users also need to install Docker Compose separately.

3. Fork the repository (https://github.com/int-brain-lab/IBL-pipeline) onto your own GitHub account.

4. Clone the forked repository.

5. Create a .env file in the cloned directory and **modify user and password values** per Step 1.

    File contents of ``.env``:
    ```
    DJ_HOST=datajoint.internationalbrainlab.org
    DJ_USER=username
    DJ_PASS=password
    ```

6. Copy your `.one_params` file into `IBL-pipeline/root` to not be prompted for Alyx login.

7. Move into the cloned directory in a terminal, then run `docker-compose up -d`.

Note: if you first build the docker container and then add `.one_params`, running ONE() in Python may still prompt you for your Alyx and FlatIron login details. In this case, do
```
`docker-compose down`
`docker image rm ibl-pipeline_datajoint:latest`
`docker-compose up -d`
`docker exec -it ibl-pipeline_datajoint_1 /bin/bash`
```

### To run example notebooks ###

8. Go to http://localhost:8888/tree in your favorite browser to open Jupyter Notebook.

9. Open "Datajoint pipeline query tutorial.ipynb".

10. Run through the notebook and feel free to experiment.

### To run your own Python scripts ###

8. If the user would like to enter the docker and run scripts through the terminal, run `docker-compose up -d`, then  run `docker exec -it ibl-pipeline_datajoint_1 /bin/bash`. Now the user should be inside the docker and is able to run scripts as needed. Go to your scripts using `cd /src/ibl-pipeline/ibl_pipeline/analyses`.

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

To turn stop the containers, run:

```bash
docker-compose -f docker-compose-local.yml down
```




# Instructions to ingest Alyx data into Amazon RDS

To insert Alyx data into the remote Amazon RDS, create a .env file in the same directory of your `docker-compose.yml`, as instructed in Step 4 above. 

Now run the docker-compose as follows, it will by default run through the file `docker-compose.yml`

```bash
docker-compose up -d
```

This will create a docker container and link to the remote Amazon RDS. Then follow the same instruction of ingestion to the local database.
