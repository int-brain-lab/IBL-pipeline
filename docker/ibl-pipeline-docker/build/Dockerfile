# syntax=docker/dockerfile:labs

# global arguments shared across different build stages
ARG IBLENV_FORK=datajoint-company
ARG IBLDATAJOINT_FORK=datajoint-company
ARG IBLDATAJOINT_REF=master
ARG IMAGE_CREATED=2022-11-11T11:11:11Z
ARG IMAGE_VERSION=v0.0.0

## Stage 1 =============================================================================
## IBL Env Rebuilder Stage
## -------------------------------------------------------------------------------------
FROM ghcr.io/${IBLENV_FORK}/dj-iblenv:latest as ibldatajoint_build

ARG IBLDATAJOINT_FORK
ARG IBLDATAJOINT_REF

ENV TZ="Europe/Lisbon"
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV LC_CTYPE=en_US.utf8
ENV QT_QPA_PLATFORM=offscreen
ENV IBL_PATH_ROOT=/int-brain-lab

SHELL [ "/bin/bash", "-elc" ]
USER root:docker
WORKDIR ${IBL_PATH_ROOT}
COPY --chown=999:999 ./requirements ./scripts ./settings /tmp/

# install debian, conda, and pip packages ----------------------------------------------
RUN <<-EOF
	xargs </tmp/apt_requirements.txt apt-get-update-install
	cp -f /tmp/*.env /tmp/.*.json ./
	cp -f /tmp/populate.py /usr/local/bin/populate
	cp -f /tmp/ONE-connect.py /usr/local/bin/ONE-connect
	cp -f /tmp/ingest.sh /usr/local/bin/ingest
	chmod 774 /usr/local/bin/ONE-connect /usr/local/bin/populate /usr/local/bin/ingest
	chown -R 999:999 /usr/local
EOF

USER 999:999
RUN <<-EOF
	touch ~/alyx.log
	touch ~/alyx_json.log
	cp -f /tmp/*.env /tmp/.*.json ~/
	micromamba activate
	micromamba install -yq --file /tmp/conda_requirements.txt
	pip install --no-cache --no-input -vr /tmp/pip_requirements.txt
	pip install --upgrade --pre "datajoint==0.12.9"
	pip uninstall -qy ibl-pipeline
	rm -Rf ./IBL-pipeline
	git clone https://github.com/${IBLDATAJOINT_FORK}/IBL-pipeline.git --branch ${IBLDATAJOINT_REF}
	pip install --no-deps --no-cache --no-input -v -e ./IBL-pipeline
	pip uninstall -qy pyopenssl
	pip install --no-cache --no-input -v pyopenssl
	conda-develop /var/www/alyx-local/alyx
	micromamba clean -fya
	conda-env export --no-builds --ignore-channels >./ibldatajoint.locked.yml
	rm -rf /tmp/*
EOF

## Stage 2 =============================================================================
## Final/Target IBL Env Image
## -------------------------------------------------------------------------------------
FROM scratch as ibldatajoint
COPY --from=ibldatajoint_build / /

ARG IMAGE_CREATED
ARG IMAGE_VERSION

# system environment
ENV TZ="Europe/Lisbon"
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV LC_CTYPE=en_US.utf8
ENV QT_QPA_PLATFORM=offscreen

# settings.py
ENV DJANGO_SECRET_KEY=
ENV ALYX_INSTANCE=
ENV ALYX_NETWORK=
ENV ALYX_LOG_FILE=
ENV ALYX_JSON_LOG_FILE=
ENV ALYX_PORT=
ENV PGPASSWORD=
ENV PGDATABASE=alyxdb
ENV PGHOST=alyx-postgres
ENV PGUSER=ibl_dev
ENV PGREADONLY=off

# ONE-api
ENV HTTP_DATA_SERVER=https://ibl.flatironinstitute.org
ENV HTTP_DATA_SERVER_LOGIN=
ENV HTTP_DATA_SERVER_PWD=
ENV ALYX_LOGIN=
ENV ALYX_PWD=
ENV ALYX_URL=
ENV CACHE_DIR=

# datajoint
ENV DJ_MODE=test
ENV DJ_HOST=host.docker.internal
ENV DJ_USER=root
ENV DJ_PASS=simple
ENV S3_ACCESS=
ENV S3_SECRET=
ENV S3_MIGRATE_BUCKET=
ENV S3_ROOT_PATH=

# misc
ENV IBL_PATH_ROOT=/int-brain-lab
ENV ALYX_SRC_PATH=/var/www/alyx-local
ENV DJANGO_SETTINGS_MODULE=alyx.settings
ENV PYTHONPATH=${ALYX_SRC_PATH}/alyx
ENV FLATIRON_SERVER_LOGIN=
ENV FLATIRON_SERVER_PWD=
ENV DJANGO_ALLOW_ASYNC_UNSAFE=true

USER 999:999
WORKDIR ${IBL_PATH_ROOT}
ENTRYPOINT [ "/bin/bash", "-lc" ]
CMD [ "tail", "-f", "/dev/null" ]

LABEL org.opencontainers.image.created="$IMAGE_CREATED"
LABEL org.opencontainers.image.version="$IMAGE_VERSION"
LABEL org.opencontainers.image.ref.name="ibldatajoint"
LABEL org.opencontainers.image.vendor="International Brain Lab"
LABEL org.opencontainers.image.title "ibldatajoint_debian_micromamba"
LABEL org.opencontainers.image.authors "Joseph Burling"
LABEL org.opencontainers.image.description "Containerized environment for routine ingestion from Alyx/flatiron to DataJoint"
