FROM datajoint/jupyter

ADD . /src/ibl-pipeline

RUN pip install -e /src/ibl-pipeline

RUN pip install "git+https://github.com/int-brain-lab/ibllib.git#egg=ibllib&subdirectory=python"
