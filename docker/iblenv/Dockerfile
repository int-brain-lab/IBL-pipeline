# syntax=docker/dockerfile:1.3-labs

# global arguments shared across build stages
ARG USERNAME=anaconda
ARG GROUPNAME=anaconda
ARG USER_UID=1000
ARG USER_GID=1000
ARG TIMEZONE="America/Chicago"

## Base conda build stage ==============================================================
FROM debian:11-slim as conda_base_debian

LABEL \
	org.opencontainers.image.authors="Joseph Burling" \
	org.opencontainers.image.title="conda_base_debian" \
	org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
	org.opencontainers.image.version="1.0" \
	org.opencontainers.image.description="Debian-based conda environment"

# inherit from global args
ARG USERNAME
ARG GROUPNAME
ARG USER_UID
ARG USER_GID
ARG TIMEZONE

# Miniforge, Mambaforge, Miniforge-pypy3, Mambaforge-pypy3
ARG CONDA_DIST=Mambaforge

ENV CONDA_DIR=/opt/local/conda
ENV PATH=${CONDA_DIR}/bin:$PATH

# set default shell to exit on first error
SHELL [ "/bin/sh", "-e", "-c" ]

# Install linux dependencies -----------------------------------------------------------
ENV TZ=${TIMEZONE}
RUN <<-EOF
	apt-get update
	apt-get -qq install -y apt-utils
	export DEBIAN_FRONTEND=noninteractive
	apt-get -qq install -y locales wget sudo
	localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
	ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime
	echo ${TZ} > /etc/timezone
	apt-get autoremove -y
	apt-get clean -y
	rm -rf /var/lib/apt/lists/*
EOF
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8

# Add directories, user/group ----------------------------------------------------------
RUN	<<-EOF
	groupadd --gid ${USER_GID} --force ${GROUPNAME}
	umask a+rwx,o-wx
	mkdir -p ${CONDA_DIR}
	cd ${CONDA_DIR}
	chown -R :${USER_GID} .*
	chgrp --no-dereference ${USER_GID} /etc/profile.d /var/log
	chmod -R 774 /etc/profile.d /var/log
	echo ". '/etc/profile.d/conda.sh'\nconda activate base" >> /etc/skel/.bashrc
	useradd --uid ${USER_UID} --gid ${USER_GID} \
		--create-home --system --groups users,sudo --shell /bin/bash ${USERNAME}
	passwd -d ${USERNAME}
	echo '${USERNAME} ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers
	install -m 771 /dev/null /usr/local/bin/conda-run
	chown :${USER_GID} /usr/local/bin/conda-run
EOF

# Entrypoint to activate specific conda environment ------------------------------------
RUN cat <<-'EOF' >> /usr/local/bin/conda-run
	#! /bin/bash --login
	[ -z "$CONDA_ENV_USER" ] && CONDA_ENV_USER=base
	set -eo pipefail
	conda activate $CONDA_ENV_USER
	exec -l "$@"
EOF

# Install conda as user ----------------------------------------------------------------
USER ${USER_UID}:${USER_GID}
WORKDIR /home/${USERNAME}
RUN <<-EOF
	URL=https://github.com/conda-forge/miniforge/releases/latest/download/${CONDA_DIST}-$(uname)-$(uname -m).sh
	wget --no-hsts --quiet -O ~/conda_install.sh ${URL}
	chmod +x ~/conda_install.sh
	~/conda_install.sh -vbup ${CONDA_DIR}
	rm ~/conda_install.sh
	find ${CONDA_DIR} -follow -type f -name '*.a' -delete
	find ${CONDA_DIR} -follow -type f -name '*.pyc' -delete
	find ${CONDA_DIR} -follow -type f -name '*.js.map' -delete
	ln -s ${CONDA_DIR}/etc/profile.d/conda.sh /etc/profile.d/conda.sh
EOF

# switch to bash as default shell for the next RUN commands, conda already in PATH
SHELL [ "/bin/bash", "-ec" ]

# configure and update base conda
RUN <<-EOF
	conda install -qy conda-build
	conda config --add channels conda-forge
	conda config --append channels defaults
	conda config --set pip_interop_enabled true
	conda clean -yiqaf
EOF

# Set default commands -----------------------------------------------------------------
ENTRYPOINT [ "conda-run" ]
CMD [ "tail", "-f", "/dev/null" ]

## IBL environment build stage =========================================================
FROM conda_base_debian as conda_base_ibl_env

LABEL \
	org.opencontainers.image.authors="Joseph Burling" \
	org.opencontainers.image.title="conda_base_ibl_env" \
	org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
	org.opencontainers.image.version="1.0" \
	org.opencontainers.image.description="Base IBL Environment Setup"

# inherit from global args
ARG USERNAME
ARG USER_UID
ARG USER_GID

# path to folder containing Dockerfile relative to the specified build context
ARG	REL_PATH_DOCKFILE=.

# conda yaml file for custom python environment, defaults to GitHub iblenv.yaml
ARG CONDA_ENV_FILE="${REL_PATH_DOCKFILE}/iblenv.yaml"

# path to list of debian dependencies to install for this image
ARG APT_REQUIREMENTS="${REL_PATH_DOCKFILE}/apt_requirements.txt"

# root path for IBL related things
ENV IBL_PATH_ROOT=/int-brain-lab

# name of conda environment used in the conda environment YAML file
ENV CONDA_ENV_USER=iblenv

# specify additional IBL paths
ENV	IBL_PATH_DATA=${IBL_PATH_ROOT}/data
ENV	IBL_PATH_SHARED=${IBL_PATH_ROOT}/shared
ENV IBL_PATH_ALYX=/var/www/alyx

# Run root:group level setup steps -----------------------------------------------------
USER 0:${USER_GID}

# set default shell to exit on first error
SHELL [ "/bin/sh", "-e", "-c" ]

# copy debian requirements file to tmp folder
COPY "${APT_REQUIREMENTS}" /tmp/apt_pkgs.txt

# install debian dependencies if APT_REQUIREMENTS is not empty
RUN <<-EOF
	[ -f /tmp/apt_pkgs.txt ] && [ -s /tmp/apt_pkgs.txt ] || exit 0
	apt-get update > /dev/null
	export DEBIAN_FRONTEND=noninteractive
	cat /tmp/apt_pkgs.txt | xargs apt-get -qq install -y
	apt-get autoremove -y
	apt-get clean -y
	rm -rf /var/lib/apt/lists/* /tmp/apt_pkgs.txt
EOF

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
	cd "${IBL_PATH_SHARED}" && chown -R ${USER_UID}:${USER_GID} .*
	cd "${IBL_PATH_DATA}/alyx" && chown -R ${USER_UID}:${USER_GID} .*
	cd "${IBL_PATH_ALYX}" && chown -R ${USER_UID}:${USER_GID} .*
	chown -R ${USER_UID}:${USER_GID} \
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
USER ${USER_UID}:${USER_GID}
WORKDIR "${IBL_PATH_ROOT}"
SHELL [ "/bin/bash", "--login", "-ec" ]

# copy over conda environment file for IBL packages
COPY --chown=${USER_UID}:${USER_GID} "${CONDA_ENV_FILE}" ./iblenv.yml

# create new conda environment w/ mamba
RUN <<-EOF
	conda config --remove-key channels
	conda config --append channels conda-forge --append channels defaults
	conda config --set channel_priority strict
	mamba env create -vv --force --file iblenv.yml
EOF

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

# install datajoint pipeline package, requirements should already be in CONDA_ENV_USER
COPY --chown=${USER_UID}:${USER_GID} \
	"${REL_PATH_DOCKFILE}/../../ibl_pipeline" \
	./ibldatajoint/ibl_pipeline

RUN <<-EOF
	cd ./ibldatajoint
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

# vscode setup
RUN mkdir -p \
		/home/$USERNAME/.vscode-server/extensions \
		/home/$USERNAME/.vscode-server-insiders/extensions

# alyx/DataJoint config initialization files saved to root IBL path
COPY --chown=${USER_UID}:${USER_GID} "${REL_PATH_DOCKFILE}/template.ingest.json" ./

# copy over entrypoint executable scripts to bin dir in PATH
COPY --chown=${USER_UID}:${USER_GID} \
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

## Target IBL environment image ========================================================
FROM scratch as iblenv_alyx
COPY --from=conda_base_ibl_env / /
LABEL \
	org.opencontainers.image.authors="Joseph Burling" \
	org.opencontainers.image.title="iblenv_alyx" \
	org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
	org.opencontainers.image.version="1.0" \
	org.opencontainers.image.description="Containerized IBL environment for routine ingestion from Alyx/flatiron to DataJoint"

# inherit from global args
ARG USERNAME
ARG USER_UID
ARG USER_GID
ARG TIMEZONE

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
USER ${USER_UID}:${USER_GID}
WORKDIR /home/${USERNAME}
EXPOSE ${ALYX_PORT}
ENTRYPOINT [ "conda-run" ]
CMD [ "tail", "-f", "/dev/null" ]
