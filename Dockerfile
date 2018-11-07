FROM datajoint/jupyter:python3.6

ADD . /src/ibl-pipeline

ADD root /root

RUN pip install -e /src/ibl-pipeline

RUN pip install "git+https://github.com/int-brain-lab/ibllib.git#egg=ibllib&subdirectory=python"
