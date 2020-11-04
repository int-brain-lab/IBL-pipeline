FROM datajoint/djlab:py3.7-debian

RUN pip install --upgrade pip
RUN pip install --upgrade datajoint

ADD . /src/IBL-pipeline
RUN pip install -e /src/IBL-pipeline


ADD ./allen_structure_tree.csv /usr/local/lib/python3.7/dist-packages/ibllib/atlas

RUN pip uninstall opencv-python -y
RUN conda install -c conda-forge opencv -y
COPY --chown=dja:anaconda ./apt_requirements.txt /tmp/apt_requirements.txt
USER root
RUN apt update
USER dja:anaconda
RUN \
    /entrypoint.sh echo "Requirements updated..." && \
    rm "${APT_REQUIREMENTS}"
