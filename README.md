# Getting started with DataJoint for IBL #

1. Email austin@vathes.com for a database username.

2. Install Docker (https://www.docker.com/). Linux users also need to install Docker Compose separately. For Mac: https://docs.docker.com/docker-for-mac/.

3. Fork the repository (https://github.com/int-brain-lab/IBL-pipeline) onto your own GitHub account by clicking on the 'Fork' button in the top right corner of Github.

4. Clone the forked repository, i.e. copy the files to your local machine by `git clone git@github.com:YourUserName/IBL-pipeline.git`. Important: do *not* clone the repo from `int-brain-lab`, but the one that you forked onto your own account!

If you don't have SSH setup, use `git clone https://github.com/YourUserName/IBL-pipeline.git`. See https://help.github.com/articles/which-remote-url-should-i-use/ for an explanation of the distinction - in the long run, it's convenient to setup SSH authorization so you don't have to type passwords every time.

5. Create a file with the name `.env` (in your favourite text editor) in the cloned directory and **modify user and password values** per Step 1.

    File contents of ``.env``:
    ```
    DJ_HOST=datajoint.internationalbrainlab.org
    DJ_USER=username
    DJ_PASS=password
    ```

6. Copy your `.one_params` file into `IBL-pipeline/root` to not be prompted for Alyx login (see https://ibllib.readthedocs.io/en/latest/02a_installation_python.html). If you have no `root` folder, create one.

Note: if you first build the docker container and then add `.one_params`, running ONE() in Python may still prompt you for your Alyx and FlatIron login details. In this case, do
	```
	docker-compose down
	docker image rm ibl-pipeline_datajoint:latest
	docker-compose up -d
	docker exec -it ibl-pipeline_datajoint_1 /bin/bash
	```

7. Now we're ready to build a Docker image. First, copy `docker-compose-template.yml` into `docker-compose.yml` - this is your own file you can customize.

To save figures in a folder outside your `IBL-pipeline` docker folder (which is good practice so you don't clutter up the Github repo), you can tell Docker to create an alias older which points to your preferred place for storing figures. 

	a. `docker-compose down`

	b. `open docker-compose.yml`

	c. add `myFullPath:/Figures_DataJoint_shortcuts` in to the `volumes:`, where `myFullPath` could for example be `~/Google Drive/Rig building WG/DataFigures/BehaviourData_Weekly/Snapshot_DataJoint/` 
	
	d. close the file

	e. `docker-compose up -d`. The first time, this will setup the Docker container which takes a bit of time.

Then save the plots from Python into `/Figures_DataJoint_shortcuts` inside the docker, then you’ll see that the plots are in the folder you want.

## To run your own Python scripts ##

8. If you would like to enter the docker and run scripts through the terminal, navigate `cd` to the IBL-pipeline directory, `chmod +x ibl_docker_setup.sh` (only needed once, will give you permission to treat this file as an 'executable') will allow you to run 
```
./ibl_docker_setup.sh
```

Which contains the following individual steps (as well as starting Docker):

```
docker-compose up -d
docker exec -it ibl-pipeline_datajoint_1 /bin/bash
```

After Docker has started, you'll be dropped in a new Terminal. To go back from there to the `IBL-pipeline/prelim_analyses` folder containing Python scripts: `cd /src/ibl-pipeline/prelim_analyses`.

Then run e.g. the behavioral snapshot code: `python behavioral_snapshot.py` or `python behavioral_overview_perlab.py`.

### Run your Python scripts after Docker is already installed for the first time ###

```
./ibl_docker_setup.sh
cd /src/ibl-pipeline/ibl_pipeline/analyses
python behavioral_snapshot.py
```

## To run example notebooks ##

9. Move into the cloned directory in a terminal, then run `docker-compose up -d`.

10. Go to http://localhost:8888/tree in your favorite browser to open Jupyter Notebook.

11. Open "Datajoint pipeline query tutorial.ipynb".

12. Run through the notebook and feel free to experiment.

### Staying up-to date ###

To stay up-to-date with the latest code from DataJoint, you might first want to check by `git remote -v`. 
If there is no upstream pointing to the int-brain-lab repository, then do `git add remote upstream https://github.com/int-brain-lab/IBL-pipeline`.

Then `git pull upstream master` will make sure that your local fork stays up to date with the original repo.

#### Contributing code ####

If you feel happy with the changes you've made, you can add, commit and push them to your own branch. Then go to https://github.com/int-brain-lab/IBL-pipeline, click 'Pull requests', 'New pull request', 'compare across forks', and select your fork of `IBL-pipeline`. If there are no merge conflicts, you can click 'Create pull request', explain what changes/contributions you've made, and and submit it to the DataJoint team for approval. 



---

# Instructions to ingest Alyx data into local database #

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

# IBL pipeline schemas #

Alyx-corresponding schemas, including, `referenall_erd.save('/images/all_erd.png')ce`, `subject`, `action`, `acquisition`, and `data`

![Alyx_corresponding erd](images/alyx_erd.png)

Schema of `ephys`
![Ephys erd](images/ephys_erd.png)

Schema of `behavior`
![Behavior erd](images/behavior_erd.png)
