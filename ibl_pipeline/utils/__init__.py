
from uuid import UUID

def is_valid_uuid(uuid):
    try:
        UUID(uuid)
        return True
    except ValueError:
        return False
