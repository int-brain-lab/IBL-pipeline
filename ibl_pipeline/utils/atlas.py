
from ibl_pipeline import reference
import datajoint as dj
import json


class BrainAtlas:

    def __init__(self):

        self.name_lookup = dict()
        for acronym, name in zip(*reference.BrainRegion.fetch(
                'acronym', 'brain_region_name')):
            self.name_lookup.update({acronym: name})

        self.atlas_dict = dict()
        for level in (dj.U('brain_region_level') &
                      reference.BrainRegion).fetch(
                          'KEY', order_by='brain_region_level'):
            for acronym, name in zip(*(reference.BrainRegion & level).fetch(
                    'acronym', 'brain_region_name',
                    order_by='graph_order')):
                if level == 0:
                    self.atlas_dict.update({str((acronym, name)): dict()})
                else:
                    self.add_region_to_dict(acronym, name)

    def add_region_to_dict(self, acronym, name):

        current_region = self.atlas_dict
        parent_list = self.get_parents(acronym)
        for region in parent_list:
            current_region = current_region[str((region, self.name_lookup[region]))]
        current_region.update({str((acronym, name)): dict()})

    @staticmethod
    def get_parents(acronym):
        parent_list = []
        while reference.ParentRegion & dict(acronym=acronym):
            acronym = (reference.ParentRegion &
                       dict(acronym=acronym)).fetch1('parent')
            parent_list.append(acronym)

        return parent_list[::-1]

    def to_json(filename='/data/atlas.json'):

        with open('atlas.json', 'w') as json_file:
            json.dump(self.atlas_dict, json_file)
