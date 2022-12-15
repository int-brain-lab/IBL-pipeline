# IBL public ingestion

## Build docker images

### Setup environment

```bash
# GITHUB_USERNAME=iamamutt
GITHUB_USERNAME=datajoint-company

PLTARCH=$(uname -m)
IMAGE_CREATED=2022-11-11T11:11:11Z
IMAGE_VERSION=v0.0.0
IBLALYX_FORK=${GITHUB_USERNAME}
IBLENV_FORK=${IBLALYX_FORK}
IBLDATAJOINT_FORK=${IBLENV_FORK}
IBLDATAJOINT_REF=public-ingest
```

### Build base image

```bash
(cd docker/local-alyx-docker/build && \
docker build \
    --platform=linux/${PLTARCH} \
    --target=iblalyx \
    --tag=ghcr.io/${GITHUB_USERNAME}/dj-iblalyx:latest \
    --build-arg IMAGE_CREATED=${IMAGE_CREATED} \
    --build-arg IMAGE_VERSION=${IMAGE_VERSION} \
    .)
```

### Build base w/ ibl environment dependencies

```bash
(cd docker/iblenv-docker/build && \
docker build \
    --platform=linux/${PLTARCH} \
    --target=iblenv \
    --tag=ghcr.io/${IBLALYX_FORK}/dj-iblenv:latest \
    --build-arg IBLALYX_FORK=${IBLALYX_FORK} \
    --build-arg IMAGE_CREATED=${IMAGE_CREATED} \
    --build-arg IMAGE_VERSION=${IMAGE_VERSION} \
    .)
```

### Build datajoint IBL ingestion image

```bash
(cd docker/ibl-pipeline-docker/build && \
docker build \
    --platform=linux/${PLTARCH} \
    --target=ibldatajoint \
    --tag=ghcr.io/${IBLDATAJOINT_FORK}/dj-ibl:latest \
    --build-arg IBLENV_FORK=${IBLENV_FORK} \
    --build-arg IBLDATAJOINT_FORK=${IBLDATAJOINT_FORK} \
    --build-arg IBLDATAJOINT_REF=${IBLDATAJOINT_REF} \
    --build-arg IMAGE_CREATED=${IMAGE_CREATED} \
    --build-arg IMAGE_VERSION=${IMAGE_VERSION} \
    .)
```
