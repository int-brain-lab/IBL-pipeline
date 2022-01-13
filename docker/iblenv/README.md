# Containerized IBL Environment

This is a containerized IBL environment for ingestion of IBL data from Alyx/flatiron to  DataJoint

## Docker build and push

For pushing to docker hub.

The Dockerfile makes use of `buildkit`. To push multiple architectures at a time, you need `buildx`. You may need to set this up before trying to build the image.

```bash
docker buildx install
docker buildx create --platform linux/arm64,linux/amd64 --name=mrbuilder --use
```

Then from the `IBL-pipeline` directory: 

```bash
cd docker/iblenv
VERSION=v1.0.1
DATE_CREATED=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
docker buildx build \
    --file=Dockerfile \
    --push \
    --platform=linux/amd64,linux/arm64 \
    --target=iblenv_alyx \
    --tag=iamamutt/iblenv_alyx:$VERSION \
    --tag=iamamutt/iblenv_alyx:latest \
    --build-arg CONDA_ENV_YAML=./iblenv.dj.yml \
    --build-arg GITHUB_USERNAME=iamamutt \
    --build-arg IMAGE_CREATED=$DATE_CREATED \
    --build-arg IMAGE_VERSION=$VERSION \
    .
```

To remove the installed buildx builder
    
```bash
docker buildx rm mrbuilder
docker buildx uninstall
```

<!--
local docker image (single platform only)

```bash
VERSION=v1.0.1
DATE_CREATED=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
docker build \
    --file=Dockerfile \
    --output=type=docker \
    --platform=linux/arm64 \
    --target=iblenv_alyx \
    --tag=iblenv_alyx:$VERSION \
    --tag=iblenv_alyx:latest \
    --build-arg CONDA_ENV_YAML=./iblenv.dj.yml \
    --build-arg GITHUB_USERNAME=iamamutt \
    --build-arg IMAGE_CREATED=$DATE_CREATED \
    --build-arg IMAGE_VERSION=$VERSION \
    .


# run image
docker run --env-file ../ibldatajoint/.env -itd iblenv_alyx:$VERSION bash


# push image to Docker Hub
docker tag iblenv_alyx:v1.0.0 iamamutt/iblenv_alyx:v1.0.0
docker tag iblenv_alyx:latest iamamutt/iblenv_alyx:latest
docker push iamamutt/iblenv_alyx:latest
```

-->

The environment variable `CONDA_ENV_YAML` allows for using a different conda environment file. Leave blank to use the default iblenv.yaml from the iblenv GitHub repo. If the standard iblenv.yaml setup fails, try a different one such as: `docker/iblenv/iblenv.dj.yml`. The path should be relative to the build context.

Change `--platform` to a valid architecture name to use another platform when building, e.g., `linux/aarch64`.
