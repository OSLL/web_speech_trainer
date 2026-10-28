from contextlib import contextmanager
from app.mongo_odm import DBManager


@contextmanager
def stored_file(identifier):
    stream = DBManager().get_file(identifier)
    if stream is None:
        raise FileNotFoundError(f"File {identifier} does not exist")
    try:
        yield stream
    finally:
        stream.close()
