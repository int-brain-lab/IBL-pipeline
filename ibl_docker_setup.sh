#!/bin/bash
#Open Docker, only if is not running
if (! docker stats --no-stream ); then
  # On Mac OS this would be the terminal command to launch Docker
  open --background -a Docker
  # Wait until Docker daemon is running and has completed initialisation
while (! docker stats --no-stream ); do
  # Docker takes a few seconds to initialize
  echo "Waiting for Docker to launch..."
  sleep 60
done
fi

docker-compose up -d

# docker exec -it ibl-pipeline_datajoint_1 bash -c "cd /prelim_analyses/" /bin/bash 
# docker-compose exec datajoint /bin/bash 
# docker exec -it ibl-pipeline_datajoint_1 bash -c "pwd" /bin/bash 
# docker exec -it ibl-pipeline_datajoint_1 bash -c "cd /src/IBL-pipeline/prelim_analyses" /bin/bash
# docker exec -it ibl-pipeline_datajoint_1 bash -c "cd /src/ibl-pipeline/prelim_analyses/behavioral_snapshot/" /bin/bash
# docker exec -it ibl-pipeline_datajoint_1 bash -c "cd /src/ibl_pipeline/prelim_analyses/behavioral_snapshots; exec /bin/bash"

docker exec -it ibl-pipeline_datajoint_1 bash -c "cd /src/IBL-pipeline/prelim_analyses/behavioral_snapshots; exec /bin/bash"