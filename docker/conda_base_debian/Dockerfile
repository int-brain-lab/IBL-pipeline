# syntax=docker/dockerfile:1.3-labs

ARG USERNAME=anaconda
ARG GROUPNAME=anaconda
ARG USER_UID=1000
ARG USER_GID=1000
ARG TIMEZONE="America/Chicago"

FROM debian:11-slim as conda_base_debian

LABEL \
org.opencontainers.image.authors="Joseph Burling" \
org.opencontainers.image.title="conda_base_debian" \
org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
org.opencontainers.image.version="1.0" \
org.opencontainers.image.description="Debian-based conda environment"

ARG USERNAME
ARG GROUPNAME
ARG USER_UID
ARG USER_GID
ARG TIMEZONE
ARG CONDA_DIST=Mambaforge

ENV CONDA_DIR=/opt/local/conda
ENV PATH=${CONDA_DIR}/bin:$PATH

# set default shell to exit on first error
SHELL [ "/bin/sh", "-e", "-c" ]

# Add user/group -----------------------------------------------------------------------
RUN groupadd --gid ${USER_GID} --force ${GROUPNAME} && \
	useradd --uid ${USER_UID} --gid ${USER_GID} \
	  --create-home --system --groups users --shell /bin/bash ${USERNAME}
USER 0:${USER_GID}
RUN	<<EOF
umask ug+rw
mkdir -p ${CONDA_DIR}
chmod -R ug+rw ${CONDA_DIR}
chgrp --no-dereference ${USER_GID} /etc/profile.d /var/log
chmod -R g+rw /etc/profile.d /var/log
EOF

# Entrypoint to activate specific conda environment ------------------------------------
RUN cat <<-'EOF' > /entrypoint
#! /bin/bash --login
[ -z "$CONDA_ENV_USER" ] && CONDA_ENV_USER=base
set -euo pipefail
conda activate $CONDA_ENV_USER
"$@"
EOF
RUN chmod a+rx,a-w /entrypoint

# Install linux dependencies -----------------------------------------------------------
ENV TZ=${TIMEZONE}
RUN <<EOF
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y apt-utils
apt-get install -y locales wget
localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
echo $TZ > /etc/timezone
apt-get autoremove -y
apt-get clean -y
rm -rf /var/lib/apt/lists/*
apt list --installed > /apt_pkgs.txt
EOF
ENV LANG=en_US.utf8 LC_ALL=en_US.utf8

# Install conda as user ----------------------------------------------------------------
USER ${USER_UID}:${USER_GID}
WORKDIR /home/${USERNAME}
RUN <<EOF
URL=https://github.com/conda-forge/miniforge/releases/latest/download/${CONDA_DIST}-$(uname)-$(uname -m).sh
wget --no-hsts --quiet -O ~/conda_install.sh ${URL}
chmod +x ~/conda_install.sh
~/conda_install.sh -vbup ${CONDA_DIR}

# do some clean up
rm ~/conda_install.sh
find ${CONDA_DIR} -follow -type f -name '*.a' -delete
find ${CONDA_DIR} -follow -type f -name '*.pyc' -delete
find ${CONDA_DIR} -follow -type f -name '*.js.map' -delete
ln -s ${CONDA_DIR}/etc/profile.d/conda.sh /etc/profile.d/conda.sh

# replicate behavior of `conda init -q bash` for interactive shells to load login scripts
echo ". '/etc/profile.d/conda.sh'" >> ~/.bashrc
echo "conda activate base" >> ~/.bashrc
EOF

# switch to bash as default shell for the next RUN commands, conda already in PATH
SHELL [ "/bin/bash", "-ec" ]

# configure and update base conda
RUN <<EOF
conda install -qy conda-build
conda config --add channels conda-forge
conda config --append channels defaults
conda config --set pip_interop_enabled true
conda clean -yiqaf
EOF

# set default command as a constantly running process
ENTRYPOINT [ "/entrypoint" ]
CMD [ "tail", "-f", "/dev/null" ]

# Conda base image ---------------------------------------------------------------------
FROM scratch as conda_base_env
LABEL \
org.opencontainers.image.authors="Joseph Burling" \
org.opencontainers.image.title="conda_base_env" \
org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
org.opencontainers.image.version="1.0" \
org.opencontainers.image.description="A base conda environment with user access"
ARG USERNAME
ARG USER_UID
ARG USER_GID
ARG TIMEZONE
ENV TZ=${TIMEZONE} LANG=en_US.utf8 LC_ALL=en_US.utf8 CONDA_ENV_USER=base
COPY --from=conda_base_debian / /
USER ${USER_UID}:${USER_GID}
WORKDIR /home/${USERNAME}
ENTRYPOINT [ "/entrypoint" ]
CMD [ "conda", "info", "-a" ]
