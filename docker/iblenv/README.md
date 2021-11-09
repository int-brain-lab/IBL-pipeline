# Containerized IBL Environment

This is a containerized IBL environment for ingestion of IBL data from Alyx/flatiron to  DataJoint

## Docker build

From the `IBL-pipeline` directory: 

```bash
cd docker/iblenv
docker buildx install
docker build \
    --file=Dockerfile \
    --platform=linux/x86_64 \
    --target=iblenv_alyx \
    --tag=iblenv_alyx:v1.0.0 \
    --tag=iblenv_alyx:latest \
    --build-arg GROUPNAME=ibl \
    --build-arg USERNAME=ibluser \
    --build-arg USER_GID=1000 \
    --build-arg USER_UID=1000 \
    --build-arg REL_PATH_DOCKFILE=docker/iblenv \
    --build-arg CONDA_ENV_FILE=docker/iblenv/iblenv.dj.yml \
    ../../.
```

Push image to Docker Hub

```bash
docker tag iblenv_alyx:v1.0.0 iamamutt/iblenv_alyx:v1.0.0
docker tag iblenv_alyx:latest iamamutt/iblenv_alyx:latest
docker push iamamutt/iblenv_alyx:latest
```

The environment variable `CONDA_ENV_FILE` allows for using a different conda environment file. Leave blank to use the default iblenv.yaml from the iblenv GitHub repo. If the standard iblenv.yaml setup fails, try the one from the shared folder: `shared/iblenv.mamba.yml`. The path should be relative to the build context.

Change `--platform` to a valid architecture name to use another platform when building, e.g., `linux/aarch64`.
