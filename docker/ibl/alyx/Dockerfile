# syntax=docker/dockerfile:1.3-labs

FROM ibl_conda_base:latest

LABEL \
org.opencontainers.image.authors="Joseph Burling" \
org.opencontainers.image.title="iblalyx" \
org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
org.opencontainers.image.version="1.0" \
org.opencontainers.image.description="Containerized Environment for Alyx DB"

ARG \
# inherit user args from base image
USERNAME= \
USER_UID= \
USER_GID= \
# path to folder containing dockerfile relative to build context
REL_PATH_DOCKFILE=docker/ibl/alyx

ENV IBL_PATH_ROOT=/int-brain-lab
ENV \
IBL_PATH_ALYX=${IBL_PATH_ROOT}/alyx \
IBL_PATH_DATA=${IBL_PATH_ROOT}/data \
IBL_PATH_SHARED=${IBL_PATH_ROOT}/shared \
# alyx/django related environment variables
PYTHONPATH="${IBL_PATH_ROOT}/alyx/alyx" \
DJANGO_SETTINGS_MODULE=alyx.settings

# change to root and group then set default shell to exit on first error
USER 0:${USER_GID}
SHELL [ "/bin/sh", "-e", "-c" ]

RUN <<EOF
# install debian dependencies
apt-get update > /dev/null
export DEBIAN_FRONTEND=noninteractive
apt-get -qq install -y libmagic1 postgresql-client-13
apt-get clean
rm -rf /var/lib/apt/lists/*

# make folders for IBL data and set permissions
umask ug+rw
mkdir -p "${IBL_PATH_ALYX}" "${IBL_PATH_DATA}" "${IBL_PATH_SHARED}"
chown -R ${USER_UID}:${USER_GID} "${IBL_PATH_ALYX}" "${IBL_PATH_DATA}" "${IBL_PATH_SHARED}"
chmod -R ug+rw,o-rwx "${IBL_PATH_ALYX}" "${IBL_PATH_DATA}" "${IBL_PATH_SHARED}"
chmod -R a+rwX /tmp
EOF

# Start new conda environment setup ----------------------------------------------------

USER ${USER_UID}:${USER_GID}
WORKDIR "${IBL_PATH_ROOT}"
SHELL [ "/bin/bash", "--login", "-ec" ]

# copy over some folder contents from build folder
COPY --chown=${USER_UID}:${USER_GID} "${REL_PATH_DOCKFILE}/environment.yml" ./

# install new conda environment
RUN <<EOF
conda config --remove-key channels
conda config --append channels conda-forge --append channels defaults
conda config --set channel_priority strict
mamba env create -vvv --force --file "environment.yml"
EOF

# download and setup alyx
RUN <<-EOF
cd alyx
wget --no-check-certificate -q -O - \
    https://github.com/cortex-lab/alyx/tarball/master | tar -xz --strip-components 1
conda activate alyxenv
cd alyx
mamba develop .
EOF

# conda cleanup and export list of all installed python packages
RUN <<EOF
conda activate alyxenv
mamba clean -qtipy
mamba env export > alyxenv.lock.yml
EOF

# finalize -----------------------------------------------------------------------------

# use custom script as entrypoint for alyx db management/setup
COPY --chown=${USER_UID}:${USER_GID} "${REL_PATH_DOCKFILE}/entrypoint" /entrypoint
RUN chmod a+x /entrypoint
ENTRYPOINT [ "/entrypoint" ]

CMD [ "dev" ]
