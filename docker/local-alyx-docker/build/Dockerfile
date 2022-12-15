# syntax=docker/dockerfile:labs

# global arguments shared across different build stages
ARG ALYX_INST_TYPE=local
ARG ALYX_GITHUB_BRANCH=master
ARG ALYX_SERVICE_NAME=alyx-apache
ARG USER_NAME=ibl_dev
ARG USER_UID=1000
ARG TIMEZONE="Europe/Lisbon"
ARG IMAGE_CREATED=2022-11-11T11:11:11Z
ARG IMAGE_VERSION=v0.0.0

## Stage 1 =============================================================================
## Core Debian Image w/ Conda (micromamba)
## -------------------------------------------------------------------------------------
FROM debian:11-slim as micromamba_debian

# inherit from global args
ARG TIMEZONE

# stage-specific args
ARG PY_VER=3.9

# system environment
ENV TZ=${TIMEZONE}
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV LC_CTYPE=en_US.utf8

# shell exit on first error within EOF sections
SHELL [ "/bin/sh", "-ec" ]

# script for common routine of installing and clearing debian packages
RUN cat <<-"EOF" >/usr/local/bin/apt-get-update-install
	#!/bin/bash
	[[ $# -lt 1 ]] && exit 0
	echo "# => Installing debian packages: '$*'"
	echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
	apt-get update >/dev/null
	apt-get -qq install -y --no-install-recommends "$@"
	apt-get autoremove -y
	apt-get clean -y
	rm -rf /var/lib/apt/lists/*
EOF

# install packages, set locale, add default group
RUN <<-EOF
	chmod a+x /usr/local/bin/apt-get-update-install
	mkdir -p -m 775 /usr/share/man/man1
	apt-get-update-install apt-utils curl locales wget bzip2 ca-certificates sudo
	localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
	ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime
	echo ${TZ} >/etc/timezone
	groupadd --gid 999 --force docker
EOF

USER 0:999

# install micromamba to /usr/local/bin
RUN <<-EOF
	cd /usr/local
	platform=$(uname | tr [:upper:] [:lower:])-$(uname -m | sed 's/amd//g' | sed 's/x86_//g')
	curl -Ls https://micro.mamba.pm/api/micromamba/$platform/latest | tar -xvj -C bin --strip-components=1 bin/micromamba
bin/micromamba
	# wget -qc "https://anaconda.org/conda-forge/micromamba/0.23.3/download/$platform/micromamba-0.23.3-0.tar.bz2" -O - | tar -xvj bin
	mv -f bin/micromamba bin/_micromamba
EOF

# conda/mamba/micromamba shell activation template
RUN cat <<-EOF >>/etc/profile.d/micromamba.sh
	export MAMBA_EXE="/usr/local/bin/_micromamba";
	export MAMBA_ROOT_PREFIX="/usr/local";
	$('/usr/local/bin/_micromamba' shell hook --shell=bash)
EOF

# for login non-interactive shells
RUN cat <<-"EOF" >>/etc/skel/.bashrc

	# >>> micromamba initialize >>>
	command -v micromamba &>/dev/null || source "/etc/profile.d/micromamba.sh"
	alias conda=micromamba
	alias mamba=micromamba
	# <<< micromamba initialize <<<
EOF

# default conda config file
RUN cat <<-EOF >/usr/local/.condarc
	envs_dirs:
	  - ~/.conda/envs
	  - /usr/local/envs
	channels:
	  - conda-forge
	  - anaconda
	channel_priority: strict
	show_channel_urls: True
	allow_softlinks: False
	pip_interop_enabled: True
	always_yes: True
EOF

# skeleton files and folders for new users
RUN <<-EOF
	mkdir -p /etc/skel/.config /etc/skel/.cache /etc/skel/.conda/envs \
		/etc/skel/.local/share /etc/skel/.local/state /etc/skel/.local/bin \
		/etc/skel/.vscode-server/extensions
	cat /etc/skel/.bashrc | tee -a /root/.bashrc /root/.profile >/dev/null
	cp -f /usr/local/.condarc /etc/skel/.conda/.condarc
	chmod a+rx /etc/profile.d/micromamba.sh

	# add a default user (no sudo)
	useradd -u 999 -g 999 --no-log-init -ms /bin/bash ubuntu
	chown -R 999:999 /usr/local
	chmod -R a+rwX,o-w,ug+s,+t,-t /usr/local
	chown -R 999:999 /var/log
	chmod -R a+rwX,o-w,ug+s,+t,-t /var/log
EOF

SHELL [ "/bin/bash",  "-elc" ]
USER 999:999
RUN <<-EOF
	# install base python and pip
	micromamba activate
	micromamba install -yvq -c conda-forge "python=${PY_VER}" pip

	# cleanup and management
	micromamba clean -fya
	micromamba update -ya
	mkdir -p /usr/local/envs
EOF

USER 0:999
RUN <<-EOF
	# updating base env only allowed for root or owner of history file
	chmod -R a+rwX,o-w,ug+s,+t,-t /usr/local
	rm -rf /tmp/*
EOF

SHELL [ "/bin/sh", "-c" ]
ENTRYPOINT [ "/bin/sh", "-c" ]
CMD [ ]

## Stage 2 =============================================================================
## IBL Alyx Image No Apache Web Server Dependencies
## -------------------------------------------------------------------------------------
FROM scratch as iblalyx_no_web
COPY --from=micromamba_debian / /

# inherit from global args
ARG ALYX_GITHUB_BRANCH
ARG ALYX_INST_TYPE
ARG TIMEZONE

# system environment
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV LC_CTYPE=en_US.utf8
ENV TZ=${TIMEZONE}

USER root:docker
COPY --chown=999:999 ./ /tmp/
SHELL [ "/bin/bash",  "-elc" ]
WORKDIR /var/www/alyx-${ALYX_INST_TYPE}

RUN <<-EOF
	# install debian packages ----------------------------------------------------------
	xargs </tmp/requirements/apt_requirements.txt apt-get-update-install

	# clone alyx source and copy settings templates ------------------------------------
	git clone https://github.com/cortex-lab/alyx.git --branch ${ALYX_GITHUB_BRANCH} .

	# copy custom alyx scripts to be found in PATH -------------------------------------
	cp -f /tmp/scripts/alyx /tmp/scripts/alyx_apache /usr/local/bin
	chmod 750 /usr/local/bin/alyx*

	# clone iblalyx source and link to appropriate alyx dirs ---------------------------
	git clone https://github.com/int-brain-lab/iblalyx.git
	# ln -s /var/www/alyx-${ALYX_INST_TYPE}/iblalyx/management/ibl_reports \
	# 	/var/www/alyx-${ALYX_INST_TYPE}/alyx/ibl_reports
	# ln -s /var/www/alyx-${ALYX_INST_TYPE}/iblalyx/management/ibl_reports/templates \
	# 	/var/www/alyx-${ALYX_INST_TYPE}/alyx/templates/ibl_reports

	# make settings template files and folders -----------------------------------------
	mkdir -p \
		./shared/local ./shared/remote \
		./cache/downloads ./cache/dumps/sql ./cache/dumps/json \
		/backups/uploaded /backups/tables
	rm -f ./alyx/alyx/settings.py
	cp -f /tmp/settings/*.py ./alyx/alyx
	cp -f /tmp/settings/su_authtoken_template.json ./alyx/alyx
	chmod -R 775 .
EOF

USER 999:999
RUN <<-EOF
	# install conda-specific packages using micromamba ---------------------------------
	micromamba activate
	micromamba install -yq --file /tmp/requirements/conda_requirements.txt

	# install packages from pypi using pip ---------------------------------------------
	pip install --no-cache --no-input -vr ./requirements.txt
	pip install --no-cache --no-input -vr /tmp/requirements/pip_requirements.txt

	# cleanup --------------------------------------------------------------------------
	micromamba clean -fya
	micromamba update -ya
	rm -rf /tmp/*
EOF

## Stage 3 =============================================================================
## IBL Alyx Image w/ Apace Web Server Dependencies
## -------------------------------------------------------------------------------------
FROM scratch as iblalyx_with_web
COPY --from=iblalyx_no_web / /

# inherit from global args
ARG ALYX_INST_TYPE
ARG TIMEZONE
ARG USER_NAME
ARG USER_UID

# system environment
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV LC_CTYPE=en_US.utf8
ENV TZ=${TIMEZONE}

USER root:docker
COPY --chown=${USER_UID}:999 ./ /tmp/
SHELL [ "/bin/bash",  "-elc" ]
WORKDIR /var/www/alyx-${ALYX_INST_TYPE}

RUN <<-EOF
	# install apache packages ----------------------------------------------------------
	xargs </tmp/requirements/apt-apache_requirements.txt apt-get-update-install

	# add new alyx admin/super user ----------------------------------------------------
	groupadd --gid ${USER_UID} ${USER_NAME} || true
	useradd -u ${USER_UID} -g 999 --no-log-init -ms /bin/bash ${USER_NAME}
	usermod -a -G users,adm,sudo,docker,${USER_NAME} ${USER_NAME}
	passwd -qd ${USER_NAME}
	echo "${USER_NAME} ALL=(ALL) NOPASSWD:ALL" >>/etc/sudoers

	# apache alyx stuff ----------------------------------------------------------------
	cp -f /tmp/apache/* ./docs/_static
	chown -R ${USER_NAME}:docker .
	chown www-data:www-data /var/www /backups/uploaded /backups/tables
	chmod -R 777 /backups
	install -m 664 /dev/null /var/log/alyx_json.log
	install -m 664 /dev/null /var/log/alyx.log
	chown -R ${USER_NAME}:docker /var/log
	install -m 664 /dev/null /etc/apache2/mods-available/wsgi.load
	chown ${USER_NAME}:docker /etc/apache2/mods-available/wsgi.load
	cp -f /tmp/apache/apache2.conf /etc/apache2/apache2.conf

	chown -R ${USER_UID}:999 /usr/local
	rm -rf /tmp/*
EOF

USER ${USER_UID}:999
RUN <<-EOF
	# update python environment --------------------------------------------------------
	micromamba activate
	pip install --no-cache --no-input -v mod_wsgi
	micromamba clean -fya
	micromamba update -ya
EOF

## Stage 4 =============================================================================
## Final/Target IBL Alyx Image - No Web
## -------------------------------------------------------------------------------------
FROM scratch as iblalyx
COPY --from=iblalyx_no_web / /

# inherit from global args
ARG ALYX_INST_TYPE
ARG ALYX_SERVICE_NAME
ARG IMAGE_CREATED
ARG IMAGE_VERSION
ARG TIMEZONE

# system environment
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV LC_CTYPE=en_US.utf8
ENV TZ=${TIMEZONE}
ENV ALYX_INSTANCE=${ALYX_INST_TYPE}
ENV ALYX_SRC_PATH=/var/www/alyx-${ALYX_INST_TYPE}
ENV ALYX_CACHE_DIR=/var/www/alyx-${ALYX_INST_TYPE}/cache
ENV ALYX_NETWORK=${ALYX_SERVICE_NAME}
ENV PYTHONPATH=/var/www/alyx-${ALYX_INST_TYPE}/alyx

# postgres
ENV PGPASSWORD=
ENV PGDATABASE=alyxlocal
ENV PGHOST=alyx-postgres
ENV PGUSER=ibl_dev
ENV PGREADONLY=off

# alyx/django related environment variables
ENV DJANGO_SECRET_KEY=
ENV DJANGO_SETTINGS_MODULE=alyx.settings

# flatiron access credentials
ENV FLATIRON_SERVER=https://ibl.flatironinstitute.org
ENV FLATIRON_SERVER_LOGIN=
ENV FLATIRON_SERVER_PWD=

# image labels
LABEL org.opencontainers.image.ref.name="iblalyx"
LABEL org.opencontainers.image.authors "Joseph Burling"
LABEL org.opencontainers.image.vendor="International Brain Lab"
LABEL org.opencontainers.image.title "iblalyx_debian_micromamba"
LABEL org.opencontainers.image.description "A debian-based, local alyx installation with a micromamba-python environment."
LABEL org.opencontainers.image.created="$IMAGE_CREATED"
LABEL org.opencontainers.image.version="$IMAGE_VERSION"

WORKDIR ${ALYX_SRC_PATH}
USER ubuntu:docker
EXPOSE 5432 ${ALYX_PORT}
SHELL [ "/bin/bash",  "-elc" ]
ENTRYPOINT [ "/bin/bash",  "-elc" ]
CMD [ "tail", "-f", "/dev/null" ]

## Stage 5 =============================================================================
## Final/Target IBL Alyx Image - Apache
## -------------------------------------------------------------------------------------
FROM scratch as iblalyx_apache
COPY --from=iblalyx_with_web / /

# inherit from global args
ARG ALYX_INST_TYPE
ARG ALYX_SERVICE_NAME
ARG IMAGE_CREATED
ARG IMAGE_VERSION
ARG TIMEZONE
ARG USER_NAME

# system environment
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV LC_CTYPE=en_US.utf8
ENV TZ=${TIMEZONE}
ENV ALYX_INSTANCE=${ALYX_INST_TYPE}
ENV ALYX_SRC_PATH=/var/www/alyx-${ALYX_INST_TYPE}
ENV ALYX_CACHE_DIR=/var/www/alyx-${ALYX_INST_TYPE}/cache
ENV ALYX_NETWORK=${ALYX_SERVICE_NAME}
ENV PYTHONPATH=/var/www/alyx-${ALYX_INST_TYPE}/alyx

# postgres
ENV PGPASSWORD=
ENV PGDATABASE=alyxlocal
ENV PGHOST=alyx-postgres
ENV PGUSER=ibl_dev
ENV PGREADONLY=off

# alyx/django related environment variables
ENV DJANGO_SECRET_KEY=
ENV DJANGO_SETTINGS_MODULE=alyx.settings

# flatiron access credentials
ENV FLATIRON_SERVER=https://ibl.flatironinstitute.org
ENV FLATIRON_SERVER_LOGIN=
ENV FLATIRON_SERVER_PWD=

# Apache ENVs
ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOCK_DIR /var/lock/apache2
ENV APACHE_LOG_DIR /var/log/apache2
ENV APACHE_PID_FILE /var/run/apache2/apache2.pid
ENV APACHE_SERVER_NAME alyx
ENV APACHE_LYNX='www-browser -dump'

# image labels
LABEL org.opencontainers.image.ref.name="iblalyx_apache"
LABEL org.opencontainers.image.authors "Joseph Burling"
LABEL org.opencontainers.image.vendor="International Brain Lab"
LABEL org.opencontainers.image.title "iblalyx_debian_micromamba_apache"
LABEL org.opencontainers.image.description "A debian-based, local alyx apache web-server installation with a micromamba-python environment."
LABEL org.opencontainers.image.created="$IMAGE_CREATED"
LABEL org.opencontainers.image.version="$IMAGE_VERSION"
# LABEL org.opencontainers.image.source="https://github.com/iamamutt/ibl-datajoint-utils"

WORKDIR ${ALYX_SRC_PATH}
USER ${USER_NAME}:docker
EXPOSE 80 443 5432 ${ALYX_PORT}
SHELL [ "/bin/bash",  "-elc" ]
ENTRYPOINT [ "alyx_apache" ]
CMD [ ]
