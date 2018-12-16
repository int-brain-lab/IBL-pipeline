FROM datajoint/jupyter:python3.6

ADD . /src/ibl-pipeline

ADD root /root

RUN pip install -e /src/ibl-pipeline

RUN pip install "git+https://github.com/int-brain-lab/ibllib.git@develop#egg=ibllib&subdirectory=python"
RUN pip install globus_sdk
