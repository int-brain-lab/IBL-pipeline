import datajoint as dj

schema = dj.schema('ibl_alyxraw')


@schema
class AlyxRaw(dj.Manual):
    definition = '''
    uuid: varchar(64)  # pk field (uuid string repr)
    ---
    model: varchar(255)  # alyx 'model'
    '''

    class Field(dj.Part):
        definition = '''
        -> master
        fname: varchar(255)  # field name
        value_idx: tinyint
        ---
        fvalue=null: varchar(10000)  # field value in the position of value_idx
        '''
