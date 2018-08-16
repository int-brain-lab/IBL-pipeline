FROM datajoint/jupyter

ADD . /src/alyx-pipeline

RUN pip install -e /src/alyx-pipeline
