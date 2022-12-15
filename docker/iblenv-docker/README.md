# `iblenv` Docker

A containerized `iblenv` environment.

## Quick Setup

1. Change to the [docker directory](./): `cd ./iblenv-docker`.

2. Rename `template.env` to `.env`. Set environment variables you want to have in the container.

3. Run `docker-compose up --detach` ([docker](https://docs.docker.com/get-docker/) and [docker compose](https://docs.docker.com/compose/install/) must be installed).

4. Check if the Jupyter server is running by going to http://127.0.0.1:8008/lab?token=1blT0k

_See below for more details._

## Docker Build and Run

Building the image depends on the base image [`dj-iblalyx:latest`](https://github.com/int-brain-lab?tab=packages&repo_name=iblalyx) found in the 'packages' section. If the platform you choose below using the `--platform` option doesn't exist for the base image, you'll have to build the base image with that platform before building the `iblenv` image.

```bash
cd iblenv-docker/build
PLTARCH=$(uname -m)
IBLALYX_FORK=datajoint-company
docker build \
    --platform=linux/${PLTARCH} \
    --target=iblenv \
    --tag=ghcr.io/${IBLALYX_FORK}/dj-iblenv:latest \
    --build-arg IBLALYX_FORK=${IBLALYX_FORK} \
    --build-arg IMAGE_CREATED=2022-11-11T11:11:11Z \
    --build-arg IMAGE_VERSION=v0.0.0 \
    .
```

```bash
docker run \
    --rm -itdu "root:docker" \
    --name iblenv_local \
    --entrypoint bash \
    ghcr.io/${IBLALYX_FORK}/dj-iblenv:latest
```

<!-- trigger rebuild 2 -->
