FROM datajoint/jupyter:python3.6

RUN pip install --upgrade pip
RUN pip install --upgrade datajoint


ADD . /src/IBL-pipeline

RUN pip install -e /src/IBL-pipeline
RUN pip install ibllib

ADD ./allen_structure_tree.csv /usr/local/lib/python3.6/dist-packages/ibllib/atlas
