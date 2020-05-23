'''
Code for deleting "unused()" external files inside the ibl pipeline
'''


import datajoint as dj
from ibl_pipeline import ephys
from ibl_pipeline.analyses import ephys as ephys_analyses
from ibl_plotting.plotting import ephys as ephys_plotting


schemas = (ephys, ephys_analyses, ephys_plotting)
stores = list(dj.config['stores'].keys())


def delete_external():
    for schema in schemas:
        for store in stores:
            print(f'Deleting {schema.__name__}: {store}')
            schema.schema.external[store].delete(delete_external_files=True)


if __name__ == "__main__":
    delete_external()
