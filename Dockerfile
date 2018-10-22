FROM datajoint/jupyter

ADD . /src/ibl-pipeline

RUN pip install -e /src/ibl-pipeline

RUN pip install git+https://github.com/shenshan/openNeuroData.git@dev
