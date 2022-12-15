# syntax=docker/dockerfile:labs

# global arguments shared across different build stages
ARG IBLALYX_FORK=datajoint-company
ARG ROOT_IBLENV_PATH=/int-brain-lab
ARG IMAGE_CREATED=2022-11-11T11:11:11Z
ARG IMAGE_VERSION=v0.0.0

## Stage 1 =============================================================================
## IBL Env Build Stage
## -------------------------------------------------------------------------------------
FROM ghcr.io/${IBLALYX_FORK}/dj-iblalyx:latest as iblenv_build

ARG ROOT_IBLENV_PATH

# system environment
ENV TZ="Europe/Lisbon"
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV LC_CTYPE=en_US.utf8
ENV QT_QPA_PLATFORM=offscreen

# shell exit on first error within EOF sections
SHELL [ "/bin/bash", "-elc" ]
COPY --chown=999:999 ./ /tmp/

# install debian, conda, and pip packages ----------------------------------------------
USER root:docker
RUN xargs </tmp/requirements/apt_requirements.txt apt-get-update-install

# clone repos and add to path ----------------------------------------------------------
USER 999:999
WORKDIR ${ROOT_IBLENV_PATH}
RUN <<-EOF
	git clone https://github.com/int-brain-lab/iblenv.git --single-branch --branch master
	git clone https://github.com/int-brain-lab/IBL-pipeline.git --single-branch --branch master
	git clone https://github.com/int-brain-lab/iblapps.git --single-branch --branch master
	git clone https://github.com/int-brain-lab/ibllib.git --single-branch --branch master
	git clone https://github.com/int-brain-lab/analysis.git --single-branch --branch master
EOF

RUN <<-EOF
	micromamba activate
	micromamba install -yq conda-build
	micromamba install -yq --file /tmp/requirements/conda_requirements.txt

	pip install --no-cache --no-input -vr /tmp/requirements/pip_requirements.txt
	pip install --no-cache --no-input --no-deps -e ./ibllib
	pip install --no-cache --no-input --no-deps -e ./iblapps
	pip install --no-cache --no-input --no-deps -e ./IBL-pipeline

	# pyqt version locked
	pip install --no-cache --no-input --no-deps easyqc

	micromamba install -yq vtk || (pip install vtk || true)
	pip install mayavi || true
EOF

RUN <<-EOF
	micromamba activate
	micromamba clean -fya || true
	# conda-env export --no-builds --ignore-channels >"${ROOT_IBLENV_PATH}/iblenv.locked.yml"
	rm -rf /tmp/*
EOF

ENTRYPOINT [ "/bin/bash", "-lc" ]
CMD [ "tail", "-f", "/dev/null" ]

## Stage 2 =============================================================================
## Final/Target IBL Env Image
## -------------------------------------------------------------------------------------
FROM scratch as iblenv
COPY --from=iblenv_build / /
USER 999:999

ARG ROOT_IBLENV_PATH
ARG IMAGE_CREATED
ARG IMAGE_VERSION

ENV IBL_PATH_ROOT=${ROOT_IBLENV_PATH}
ENV TZ="Europe/Lisbon"
ENV LANG=en_US.utf8
ENV LC_ALL=en_US.utf8
ENV LANGUAGE=en_US.utf8
ENV LC_CTYPE=en_US.utf8
ENV QT_QPA_PLATFORM=offscreen
ENV PYTHONPATH=/var/www/alyx-local/alyx
ENV DJANGO_SETTINGS_MODULE=alyx.settings

WORKDIR ${ROOT_IBLENV_PATH}
ENTRYPOINT [ "/bin/bash", "-lc" ]
CMD [ ]

LABEL org.opencontainers.image.ref.name="iblenv"
LABEL org.opencontainers.image.authors "Joseph Burling"
LABEL org.opencontainers.image.vendor="International Brain Lab"
LABEL org.opencontainers.image.title "iblenv_debian_micromamba"
LABEL org.opencontainers.image.description "A unified environment for all IBL repositories."
LABEL org.opencontainers.image.created="$IMAGE_CREATED"
LABEL org.opencontainers.image.version="$IMAGE_VERSION"
