FROM debian:11-slim

LABEL \
    org.opencontainers.image.authors="Joseph Burling" \
    org.opencontainers.image.title="iblalyx" \
    org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    org.opencontainers.image.version="1.0" \
    org.opencontainers.image.description="Containerized Environment for Alyx DB"

ARG USERNAME=alyxadmin
ARG GROUPNAME=alyxdb
ARG USER_UID=1000
ARG USER_GID=1000
ARG TIMEZONE="America/Chicago"

# path to folder containing dockerfile relative to build context
ARG REL_PATH_DOCKFILE=docker/ibl/alyx

# for timezone and locale setup
ENV TZ=${TIMEZONE}

# root path for IBL related things
ENV IBL_PATH_ROOT=/int-brain-lab

# alyx path as specified on github repo, other paths shared with ibl containers
ENV IBL_PATH_ALYX=/var/www/alyx \
    IBL_PATH_DATA=${IBL_PATH_ROOT}/data \
    IBL_PATH_SHARED=${IBL_PATH_ROOT}/shared

# postgres/alyx/django related environment variables
ENV PGUSER=${USERNAME} \
    PGDATABASE=${GROUPNAME} \
    PYTHONPATH="${IBL_PATH_ALYX}/alyx" \
    DJANGO_SETTINGS_MODULE=alyx.settings \
    ALYX_SECRET_KEY=0xdeadbeef \
    ALYX_PORT=8000

# python aliases
RUN echo "alias python=python3" | tee -a /etc/skel/.bash_aliases /etc/bash.bashrc

# install debian dependencies and set locale
RUN apt-get update && \
    apt-get -qq install -y apt-utils && \
    DEBIAN_FRONTEND=noninteractive apt-get -qq install -y \
      apache2 \
      libapache2-mod-wsgi-py3 \
      libmagic1 \
      locales \
      net-tools \
      postgresql-client-13 \
      python3-dev \
      python3-pip  \
      virtualenv \
      sudo \
      wget && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo ${TZ} > /etc/timezone && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*
ENV LANG=en_US.utf8 LC_ALL=en_US.utf8

# add custom user and group
RUN groupadd --gid ${USER_GID} --force ${GROUPNAME} && \
    useradd  --uid ${USER_UID} --gid ${USER_GID} \
      --create-home --system --groups users,sudo --shell /bin/bash ${USERNAME} && \
    passwd -d ${USERNAME} && \
    echo '${USERNAME} ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

# set file permissions for user and django
USER 0:${USER_GID}
RUN umask 001 && \
    install -m 776 /dev/null /var/log/alyx.log && \
    install -m 776 /dev/null /var/log/alyx_json.log && \
    install -m 776 /dev/null /etc/apache2/sites-available/001-alyx.conf && \
    mkdir -p \
      "${IBL_PATH_ALYX}/uploaded" \
      "${IBL_PATH_DATA}/alyx" \
      "${IBL_PATH_SHARED}" && \
    cd "${IBL_PATH_DATA}/alyx" && \
    chown -R ${USER_UID}:${USER_GID} \
      .* \
      "${IBL_PATH_SHARED}" && \
    cd "${IBL_PATH_ALYX}" && \
    chown -R ${USER_UID}:${USER_GID} \
      .* \
      /var/log \
      /etc/apache2/sites-available/001-alyx.conf && \
    chown www-data:www-data \
      "${IBL_PATH_ALYX}/uploaded" \
      /var/www

# switch to user and alyx dir, use bash
USER ${USER_UID}:${USER_GID}
WORKDIR "${IBL_PATH_ALYX}"
SHELL [ "/bin/bash", "-c" ]

# install alyx
ENV VIRTUAL_ENV="${IBL_PATH_ALYX}/alyxvenv"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}:/home/${USERNAME}/.local/bin"
RUN virtualenv alyxvenv --python=python3 && \
    echo "alias alyxenv='source ${VIRTUAL_ENV}/bin/activate'" >> ~/.bashrc
RUN wget --no-check-certificate -q -O - \
      https://github.com/cortex-lab/alyx/tarball/master | \
      tar -xz --strip-components 1 && \
    source ${VIRTUAL_ENV}/bin/activate && \
    python -m pip install --upgrade pip wheel && \
    pip install -r requirements.txt && \
    sudo /usr/sbin/a2enmod -q wsgi

# use custom script as entrypoint for alyx db management/setup
USER 0:0
COPY "${REL_PATH_DOCKFILE}/entrypoint" /usr/local/bin/alyx
RUN chmod 771 /usr/local/bin/alyx && chown ${USER_UID}:${USER_GID} /usr/local/bin/alyx
USER ${USER_UID}:${USER_GID}
EXPOSE ${ALYX_PORT}
ENTRYPOINT [ "alyx" ]
CMD [ "dev" ]

# these env variables should be specified during build or in a compose file
ENV PGHOST=
ENV PGPASSWORD=
ENV HTTP_DATA_SERVER_LOGIN=
ENV HTTP_DATA_SERVER_PWD=
