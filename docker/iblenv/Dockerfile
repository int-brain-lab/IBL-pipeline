# syntax=docker/dockerfile:1.3-labs

# global arguments shared across build stages
ARG USER_NAME=ibluser
ARG USER_UID=1000
ARG TIMEZONE="America/Chicago"
ARG IMAGE_CREATED=2021-11-11T11:11:11Z
ARG IMAGE_VERSION=v0.0.0a

## IBL environment build stage =========================================================
FROM ghcr.io/iamamutt/conda_base:latest as conda_base_ibl_env

# inherit from global args
ARG USER_NAME
ARG USER_UID
ARG TIMEZONE

# path to folder containing Dockerfile relative to the specified build context
ARG	REL_PATH_DOCKFILE=.

# conda yaml file for custom python environment, defaults to GitHub iblenv.yaml
ARG CONDA_ENV_YAML="${REL_PATH_DOCKFILE}/iblenv.yaml"

# path to list of debian dependencies to install for this image
ARG APT_REQUIREMENTS="${REL_PATH_DOCKFILE}/apt_requirements.txt"

# for downloading IBL-pipeline package code
ARG GITHUB_USERNAME=datajoint

# root path for IBL related things
ENV IBL_PATH_ROOT=/int-brain-lab

# name of conda environment used in the conda environment YAML file
ENV CONDA_ENV_USER=iblenv

# specify additional IBL paths
ENV	IBL_PATH_DATA=${IBL_PATH_ROOT}/data
ENV	IBL_PATH_SHARED=${IBL_PATH_ROOT}/shared
ENV IBL_PATH_ALYX=/var/www/alyx

# directory where default apt_requirements.txt and environment.yml are located
WORKDIR /srv/conda

# set default shell to exit on first error
SHELL [ "/bin/sh", "-e", "-c" ]

# copy debian requirements file, overwriting existing apt_requirements.txt
COPY "${APT_REQUIREMENTS}" ./apt_requirements.txt

# copy conda environment file for IBL packages, overwriting existing environment.yml
COPY "${CONDA_ENV_YAML}" ./environment.yml

# initialize new user, install debian packages, setup conda environment
RUN init-env

# add sudo support for new user
RUN echo ${USER_NAME} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USER_NAME} && \
    chmod 0440 /etc/sudoers.d/${USER_NAME}

# make files/folders for IBL data and alyx then change ownership
RUN <<-EOF
	umask 001
	mkdir -p \
		"${IBL_PATH_ALYX}/uploaded" \
		"${IBL_PATH_DATA}/alyx" \
		"${IBL_PATH_SHARED}"
	install -m 776 /dev/null /var/log/alyx.log
	install -m 776 /dev/null /var/log/alyx_json.log
	install -m 776 /dev/null /etc/apache2/sites-available/001-alyx.conf
	install -m 771 /dev/null /etc/apache2/mods-available/wsgi.load
	install -m 771 /dev/null /etc/apache2/conf-available/servername.conf
	cd "${IBL_PATH_SHARED}" && chown -R ${USER_NAME} .*
	cd "${IBL_PATH_DATA}/alyx" && chown -R ${USER_NAME} .*
	cd "${IBL_PATH_ALYX}" && chown -R ${USER_NAME} .*
	chown -R ${USER_NAME} \
		/var/log \
		/var/log/alyx* \
		/etc/apache2/sites-available/001-alyx.conf \
		/etc/apache2/mods-available/wsgi.load \
		/etc/apache2/conf-available/servername.conf
	chown www-data:www-data "${IBL_PATH_ALYX}/uploaded" /var/www
	chmod -R a+rwX /tmp
EOF

# Start new conda environment setup ----------------------------------------------------

# setup conda environment as user from root IBL path
USER ${USER_NAME}
WORKDIR "${IBL_PATH_ROOT}"
SHELL [ "/bin/bash", "--login", "-ec" ]

# Install IBL related python packages --------------------------------------------------

# alyx source code
RUN <<-EOF
	cd "${IBL_PATH_ALYX}"
	wget --no-check-certificate -q -O - \
		https://github.com/cortex-lab/alyx/tarball/master | \
		tar -xz --strip-components 1
	conda activate ${CONDA_ENV_USER}
	pip install --no-input mod_wsgi
	pip install --no-input -vr requirements.txt
	mamba develop ./alyx
EOF

# install iblapps, requirements should already be in CONDA_ENV_USER
RUN <<-EOF
	git clone --branch develop https://github.com/int-brain-lab/iblapps.git
	cd ./iblapps
	conda activate ${CONDA_ENV_USER}
	mamba develop --build_ext .
EOF

RUN <<-EOF
	git clone --branch develop https://github.com/int-brain-lab/ibllib.git
	cd ./ibllib
	conda activate ${CONDA_ENV_USER}
	mamba develop --build_ext .
EOF

# install mayavi from source, requirements should already be in CONDA_ENV_USER
RUN <<-EOF
	git clone https://github.com/enthought/mayavi.git
	cd ./mayavi
	conda activate ${CONDA_ENV_USER}
	mamba develop --build_ext .
EOF

# install IBL-pipeline/ibl_pipeline only
RUN <<-EOF
	mkdir -p /tmp/ibldatajoint ./IBL-pipeline
	cd /tmp/ibldatajoint
	wget --no-check-certificate -q -O - \
		https://github.com/${GITHUB_USERNAME}/IBL-pipeline/tarball/new-ingestion | \
		tar -xz --strip-components 1
	cd "${IBL_PATH_ROOT}/IBL-pipeline"
	mv -v /tmp/ibldatajoint/ibl_pipeline .
	rm -rf /tmp/ibldatajoint
	conda activate ${CONDA_ENV_USER}
	pip install --upgrade --pre "datajoint==0.12.9" # revert to old version
	mamba develop .
EOF

# Finalize setup -----------------------------------------------------------------------

# conda cleanup and export list of all installed python packages
RUN <<-EOF
	conda activate ${CONDA_ENV_USER}
	mamba clean -qtipy
	mamba env export > ${CONDA_ENV_USER}.lock.yml
EOF

# add vscode folders to home directory
RUN \
    mkdir -p \
        /home/${USER_NAME}/.vscode-server/extensions \
        /home/${USER_NAME}/.vscode-server-insiders/extensions && \
    chown -R ${USER_NAME} \
        /home/${USER_NAME}/.vscode-server \
        /home/${USER_NAME}/.vscode-server-insiders

# alyx/DataJoint config initialization files saved to root IBL path
COPY --chown=${USER_NAME} "${REL_PATH_DOCKFILE}/template.ingest.json" ./

# copy over entrypoint executable scripts to bin dir in PATH
COPY --chown=${USER_NAME} \
		"${REL_PATH_DOCKFILE}/ingest" \
		"${REL_PATH_DOCKFILE}/alyx" \
		"${REL_PATH_DOCKFILE}/config_init.py" \
		"${REL_PATH_DOCKFILE}/populate.py" \
		/usr/local/bin/

# make executable
RUN chmod 771 \
		/usr/local/bin/config_init.py \
		/usr/local/bin/populate.py \
		/usr/local/bin/alyx \
		/usr/local/bin/ingest

ARG IMAGE_CREATED
ARG IMAGE_VERSION
LABEL org.opencontainers.image.authors="Joseph Burling"
LABEL org.opencontainers.image.title="conda_base_ibl_env"
LABEL org.opencontainers.image.created="$IMAGE_CREATED"
LABEL org.opencontainers.image.version="$IMAGE_VERSION"
LABEL org.opencontainers.image.description="Base IBL Environment Setup"

## Target IBL environment image ========================================================
FROM scratch as iblenv_alyx
COPY --from=conda_base_ibl_env / /

# inherit from global args
ARG USER_NAME
ARG USER_UID
ARG TIMEZONE
ARG IMAGE_CREATED
ARG IMAGE_VERSION

LABEL org.opencontainers.image.authors="Joseph Burling"
LABEL org.opencontainers.image.title="iblenv_alyx"
LABEL org.opencontainers.image.created="$IMAGE_CREATED"
LABEL org.opencontainers.image.version="$IMAGE_VERSION"
LABEL org.opencontainers.image.description="Containerized IBL environment for routine ingestion from Alyx/flatiron to DataJoint"

# debian environment variables
ENV TZ=${TIMEZONE}
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8

# iblenv environment variables
ENV CONDA_ENV_USER=iblenv
ENV IBL_PATH_ROOT=/int-brain-lab
ENV	IBL_PATH_DATA=${IBL_PATH_ROOT}/data
ENV IBL_PATH_SHARED=${IBL_PATH_ROOT}/shared
ENV IBL_PATH_ALYX=/var/www/alyx

# postgres/alyx/django related environment variables
ENV PGUSER=alyxadmin
ENV PGDATABASE=alyxdb
ENV PGHOST=pgserver
ENV ALYX_SECRET_KEY=0xdeadbeef
ENV ALYX_PORT=8000
ENV DJANGO_SETTINGS_MODULE=alyx.settings
ENV DJANGO_ALLOW_ASYNC_UNSAFE=true
ENV PYTHONPATH="${IBL_PATH_ALYX}/alyx"
ENV PGPASSWORD=supersecretdbpass

# alyx/flatiron access credentials
ENV HTTP_DATA_SERVER=https://ibl.flatironinstitute.org
ENV HTTP_DATA_SERVER_LOGIN=
ENV HTTP_DATA_SERVER_PWD=
ENV ALYX_LOGIN=
ENV ALYX_PWD=
ENV ALYX_URL=

# DataJoint config
ENV DJ_MODE=test
ENV DJ_HOST=
ENV DJ_USER=
ENV DJ_PASS=
ENV S3_ACCESS=
ENV S3_SECRET=
ENV S3_MIGRATE_BUCKET=
ENV S3_ROOT_PATH=

# final setup
USER ${USER_NAME}
WORKDIR /home/${USER_NAME}
EXPOSE ${ALYX_PORT}
ENTRYPOINT [ "conda-run" ]
CMD [ "tail", "-f", "/dev/null" ]
