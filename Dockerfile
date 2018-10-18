FROM datajoint/jupyter

ADD ./ibl-pipeline /src/ibl-pipeline

ADD ./openNeuroData /src/openNeuroData

RUN pip install -e /src/ibl-pipeline

RUN pip install -e /src/openNeuroData

# RUN pip install -r /src/ibl-pipeline/dev_requirements.txt
