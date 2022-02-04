# syntax=docker/dockerfile:labs

# global arguments shared across build stages
ARG NEW_USER_NAME=ibl
ARG NEW_USER_GROUP=ibl
ARG IMAGE_CREATED=2021-11-11T11:11:11Z
ARG IMAGE_VERSION=v0.0.0a
ARG ROOT_ENV_PATH=/int-brain-lab
ARG ROOT_ALYX_PATH=/var/www/alyx-main/alyx

## IBL environment build stage =========================================================
FROM ghcr.io/iamamutt/conda_base:latest as conda_base_ibl_env

# inherit from global args
ARG IMAGE_CREATED
ARG IMAGE_VERSION
ARG NEW_USER_NAME
ARG NEW_USER_GROUP
ARG ROOT_ENV_PATH
ARG ROOT_ALYX_PATH

# # set default shell to exit on first error
SHELL [ "/bin/sh", "-ec" ]

# create new user  ---------------------------------------------------------------------

# user created based on the NEW_USER_* arguments
ENV NEW_USER_SUDO=true
RUN init-new-user
USER root:${NEW_USER_GROUP}

# setup root IBL directories -----------------------------------------------------------

# root path for IBL related things and other IBL subdirectories
ENV IBL_PATH_ROOT=${ROOT_ENV_PATH}
ENV	IBL_PATH_DATA=${IBL_PATH_ROOT}/data
ENV	IBL_PATH_SHARED=${IBL_PATH_ROOT}/shared
ENV IBL_PATH_ALYX=${ROOT_ALYX_PATH}

# make files/folders for IBL data and alyx then change ownership
RUN <<-EOF
	mkdir -p -m 6775 \
		${IBL_PATH_ALYX} \
		${IBL_PATH_DATA}/alyx/cache \
		${IBL_PATH_SHARED}/data
	chown -R root:${NEW_USER_GROUP} ${IBL_PATH_ROOT}
EOF

WORKDIR ${IBL_PATH_ROOT}

# Copy IBL-pipeline package content ----------------------------------------------------

# set path to where repo content will be then copy over content and chown to new user
ENV IBL_PKG_DJ=${IBL_PATH_ROOT}/IBL-pipeline
COPY --chown=${NEW_USER_NAME}:${NEW_USER_GROUP} ./ ${IBL_PKG_DJ}/

# file for custom python environment relative to context root,
#   defaults to DataJoint version of iblenv file
ARG CONDA_ENV_YAML=docker/image/pkgs/iblenv.dj.yml

# relative path to list of debian dependencies to install
ARG APT_REQUIREMENTS=docker/image/pkgs/apt_requirements.txt

# copy apt-get dependencies, conda environment yml, datajoint config template, entrypoints
RUN <<-EOF
	cp -f \
		${IBL_PKG_DJ}/${CONDA_ENV_YAML} \
		/srv/conda/environment.yml
	cp -f \
		${IBL_PKG_DJ}/${APT_REQUIREMENTS} \
		/srv/conda/apt_requirements.txt
	cp -f \
		${IBL_PKG_DJ}/docker/image/config.json \
		${IBL_PATH_ROOT}/config.json
	cp -fR ${IBL_PKG_DJ}/docker/image/scripts/* /usr/local/bin
	chmod 775 /usr/local/bin/*
	chown ${NEW_USER_NAME}:${NEW_USER_GROUP} /usr/local/bin/*
EOF

# Install debian package dependencies  -------------------------------------------------

# using file from /srv/conda/apt_requirements.txt
RUN init-apt-deps

# Download package source code ---------------------------------------------------------
RUN <<-EOF
	git clone https://github.com/int-brain-lab/iblapps.git --branch develop --single-branch ${IBL_PATH_ROOT}/ibllib-repo
	git clone https://github.com/int-brain-lab/ibllib.git --branch develop --single-branch
	git clone https://github.com/cortex-lab/alyx.git --branch dev --single-branch ${IBL_PATH_ALYX}/
EOF

# add alyx related files and permissions
RUN <<-EOF
	mkdir -p -m 6775 ${IBL_PATH_ALYX}/../uploaded
	chown -R ${NEW_USER_NAME}:${NEW_USER_GROUP} ${IBL_PATH_ALYX}/..
	chmod -R g+rwX ${IBL_PATH_ALYX}/..
	chown www-data:www-data /var/www ${IBL_PATH_ALYX}/../uploaded
	usermod -a -G adm ${NEW_USER_NAME}
	install -m 770 /dev/null /etc/apache2/conf-available/servername.conf
	install -m 770 /dev/null /etc/apache2/mods-available/wsgi.load
	install -m 770 /dev/null /etc/apache2/sites-available/001-alyx.conf
	install -m 770 /dev/null /var/log/alyx_json.log
	install -m 770 /dev/null /var/log/alyx.log
EOF

# Setup new conda environment  ---------------------------------------------------------

USER ${NEW_USER_NAME}:condauser
SHELL [ "/bin/bash", "--login", "-ec" ]
ENV QT_QPA_PLATFORM=offscreen
RUN init-conda-env

RUN <<-EOF
	conda activate ${CONDA_ENV_USER}
	pip install --no-input -vr ${IBL_PATH_ALYX}/requirements.txt
	pip install --upgrade --pre "datajoint==0.12.9" # revert to old version
	cd ${IBL_PATH_ALYX}/alyx
	mamba develop .
	cd ${IBL_PATH_ROOT}/ibllib-repo
	mamba develop .
	cd ${IBL_PATH_ROOT}/iblapps
	mamba develop .
	cd ${IBL_PATH_ROOT}/IBL-pipeline/.
	mamba develop .
	mamba update --all
EOF

USER root:condauser
RUN <<-EOF
	source /home/${NEW_USER_NAME}/.bash_profile
	rm -f /home/${NEW_USER_NAME}/*.lock.yml
	conda activate ${CONDA_ENV_USER}
	mamba clean -qya
	mamba env export --no-builds > ${CONDA_ENV_USER}.lock.yml
	chgrp -fc ${NEW_USER_GROUP} ${CONDA_ENV_USER}.lock.yml
	mkdir -p \
		/home/${NEW_USER_NAME}/.vscode-server/extensions \
		/home/${NEW_USER_NAME}/.vscode-server-insiders/extensions
	chmod -R 777 /home/${NEW_USER_NAME}/.vscode-server*
	chown -R ${NEW_USER_NAME}:${NEW_USER_GROUP} /home/${NEW_USER_NAME}/.vscode-server*
EOF

## Target IBL environment image ========================================================
FROM scratch as iblenv_alyx
COPY --from=conda_base_ibl_env / /

# inherit from global args
ARG NEW_USER_NAME
ARG NEW_USER_GROUP
ARG IMAGE_CREATED
ARG IMAGE_VERSION
ARG ROOT_ENV_PATH
ARG ROOT_ALYX_PATH

LABEL org.opencontainers.image.authors="Joseph Burling"
LABEL org.opencontainers.image.title="iblenv_alyx"
LABEL org.opencontainers.image.created="$IMAGE_CREATED"
LABEL org.opencontainers.image.version="$IMAGE_VERSION"
LABEL org.opencontainers.image.description="Containerized IBL environment for routine ingestion from Alyx/flatiron to DataJoint"

# debian environment variables
ENV TZ="America/Chicago"
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8

# iblenv environment variables
ENV USER_NAME=${NEW_USER_NAME}
ENV USER_GROUP=${NEW_USER_GROUP}
ENV IBL_PATH_ROOT=${ROOT_ENV_PATH}
ENV	IBL_PATH_DATA=${IBL_PATH_ROOT}/data
ENV IBL_PATH_SHARED=${IBL_PATH_ROOT}/shared
ENV IBL_PATH_ALYX=${ROOT_ALYX_PATH}

# postgres/alyx/django related environment variables
ENV PGUSER=alyxadmin
ENV PGDATABASE=alyxdb
ENV PGHOST=pgserver
ENV POSTGRES_PASSWORD=

ENV DJANGO_SECRET_KEY=
ENV DJANGO_SETTINGS_MODULE=alyx.settings
ENV DJANGO_ALLOW_ASYNC_UNSAFE=true
ENV PYTHONPATH=${IBL_PATH_ALYX}/alyx

# alyx/flatiron access credentials
ENV HTTP_DATA_SERVER=https://ibl.flatironinstitute.org
ENV HTTP_DATA_SERVER_LOGIN=
ENV HTTP_DATA_SERVER_PWD=
ENV ALYX_PORT=8000
ENV ALYX_LOGIN=
ENV ALYX_PWD=
ENV ALYX_URL=

# DataJoint config
ENV DJ_MODE=test
ENV DJ_HOST=host.docker.internal
ENV DJ_USER=root
ENV DJ_PASS=simple
ENV S3_ACCESS=
ENV S3_SECRET=
ENV S3_MIGRATE_BUCKET=
ENV S3_ROOT_PATH=

# final setup
USER ${NEW_USER_NAME}:${NEW_USER_GROUP}
WORKDIR /home/${NEW_USER_NAME}
EXPOSE ${ALYX_PORT}
ENTRYPOINT [ "sudo-run" ]
CMD [ "tail", "-f", "/dev/null" ]
