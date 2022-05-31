import inspect

from datajoint.user_tables import UserTable


def list_tables(schema):
    for k in dir(schema):
        t = getattr(schema, k)
        if inspect.isclass(t) and issubclass(t, UserTable):
            print(k)
