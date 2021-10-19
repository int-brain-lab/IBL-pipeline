# syntax=docker/dockerfile:1.3-labs

FROM ibl_conda_base:latest

LABEL \
org.opencontainers.image.authors="Joseph Burling" \
org.opencontainers.image.title="iblenv" \
org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
org.opencontainers.image.version="1.0" \
org.opencontainers.image.description="Containerized IBL Environment"

ARG \
# inherit user args from base image
USERNAME= \
USER_UID= \
USER_GID= \
# conda yaml file for custom python environment, defaults to GitHub iblenv.yaml if empty
CONDA_ENV_FILE= \
# path to folder containing dockerfile relative to build context
REL_PATH_DOCKFILE=docker/ibl/ingest \
# path to .one_params
DOT_ONE_FILE= \
# path to list of debian dependencies to install
APT_REQUIREMENTS="${REL_PATH_DOCKFILE}/apt_requirements.txt"


ENV IBL_PATH_ROOT=/int-brain-lab
ENV \
CONDA_ENV_USER=iblenv \
IBL_PATH_DATA=${IBL_PATH_ROOT}/data \
IBL_PATH_SHARED=${IBL_PATH_ROOT}/shared

# change to root and group then set default shell to exit on first error
USER 0:${USER_GID}
SHELL [ "/bin/sh", "-e", "-c" ]

COPY "${APT_REQUIREMENTS}" /tmp/apt_requirements.txt
RUN <<EOF
# will only install additional debian dependencies if apt_requirements.txt is not empty
[ -f /tmp/apt_requirements.txt ] && [ -s /tmp/apt_requirements.txt ] || exit 0
apt-get update > /dev/null
export DEBIAN_FRONTEND=noninteractive
cat /tmp/apt_requirements.txt | xargs apt-get -qq install -y
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/apt_requirements.txt
apt list --installed > ~/apt_pkgs.txt

# make folders for IBL data and source code
umask ug+rw
mkdir -p "${IBL_PATH_DATA}" "${IBL_PATH_SHARED}"
chown -R ${USER_UID}:${USER_GID} "${IBL_PATH_DATA}" "${IBL_PATH_SHARED}"
chmod -R ug+rw,o-rwx "${IBL_PATH_DATA}" "${IBL_PATH_SHARED}"
chmod -R a+rwX /tmp
EOF

# Start new conda environment setup ----------------------------------------------------
USER ${USER_UID}:${USER_GID}
WORKDIR "${IBL_PATH_ROOT}"
SHELL [ "/bin/bash", "--login", "-ec" ]

# dummy file README.md is required, path set in CONDA_ENV_FILE is optional
COPY --chown=${USER_UID}:${USER_GID} \
	 ["${REL_PATH_DOCKFILE}/README.md", "${CONDA_ENV_FILE}*", "./"]

RUN <<EOF
# use iblenv from GitHub as default conda environment if CONDA_ENV_FILE doesnt exist
git clone https://github.com/int-brain-lab/iblenv.git
CONDA_YAML="${IBL_PATH_ROOT}/$(basename ${CONDA_ENV_FILE})"
[ -f "${CONDA_YAML}" ] || CONDA_YAML=iblenv/iblenv.yaml

# conda config setup
conda config --remove-key channels
conda config --append channels conda-forge --append channels defaults
conda config --set channel_priority strict

# install new conda environment
mamba env create -vvv --force --file "${CONDA_YAML}"
EOF

# Install pipeline related packages ----------------------------------------------------
# install mayavi from source, requirements should already be in CONDA_ENV_USER
RUN <<EOF
git clone https://github.com/enthought/mayavi.git
conda activate ${CONDA_ENV_USER}
cd ./mayavi
mamba develop --build_ext .
EOF

# install iblapps, requirements should already be in CONDA_ENV_USER
RUN <<EOF
git clone --branch develop https://github.com/int-brain-lab/iblapps.git
conda activate ${CONDA_ENV_USER}
cd ./iblapps
mamba develop --build_ext .
EOF

# install datajoint pipeline package, requirements should already be in CONDA_ENV_USER
COPY --chown=${USER_UID}:${USER_GID} ./ibl_pipeline ./ibldatajoint/ibl_pipeline
RUN <<EOF
conda activate ${CONDA_ENV_USER}
pip install --upgrade --pre "datajoint==0.12.9" # revert to old version
cd ./ibldatajoint
mamba develop .
EOF

# finalize -----------------------------------------------------------------------------
RUN <<-EOF
# conda cleanup and export list of all installed python packages
conda activate ${CONDA_ENV_USER}
mamba clean -qtipy
mamba env export > ${CONDA_ENV_USER}.lock.yml

# vscode setup
mkdir -p \
	/home/$USERNAME/.vscode-server/extensions \
	/home/$USERNAME/.vscode-server-insiders/extensions
EOF

COPY --chown=${USER_UID}:${USER_GID} ${DOT_ONE_FILE} /home/${USERNAME}/.one_params
ENTRYPOINT [ "/entrypoint" ]
CMD [ "tail", "-f", "/dev/null" ]
