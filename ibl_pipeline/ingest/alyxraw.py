import datajoint as dj

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_alyxraw')


@schema
class AlyxRaw(dj.Manual):
    definition = '''
    uuid: uuid  # pk field (uuid string repr)
    ---
    model: varchar(255)  # alyx 'model'
    '''

    class Field(dj.Part):
        definition = '''
        -> master
        fname: varchar(255)  # field name
        value_idx: tinyint
        ---
        fvalue=null: varchar(40000)  # field value in the position of value_idx
        index (fname)
        '''
