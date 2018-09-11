FROM datajoint/jupyter

ADD . /src/ibl-pipeline

RUN pip install -e /src/ibl-pipeline
