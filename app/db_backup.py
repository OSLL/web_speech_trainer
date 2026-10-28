"""Write MongoDB BSON and index metadata into an atomically published ZIP."""

import os
from pathlib import Path
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

from bson import BSON, json_util
from pymodm.connection import _get_db

from app.config import Config
from app.mongo_odm import DBManager

BACKUP_FILENAMES = ("backup.zip", "backup_nochunks.zip")


def create_db_dump(name):
    if name not in BACKUP_FILENAMES:
        raise ValueError("Unknown backup filename")
    DBManager()
    database = _get_db()
    directory = Path(Config.c.constants.backup_path).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".backup-", suffix=".zip", dir=directory
    )
    os.close(descriptor)
    try:
        with ZipFile(
            temporary, "w", compression=ZIP_DEFLATED, allowZip64=True
        ) as archive:
            for info in database.list_collections(filter={"type": "collection"}):
                collection_name = info["name"]
                if collection_name.startswith("system.") or (
                    name == "backup_nochunks.zip" and collection_name == "fs.chunks"
                ):
                    continue
                collection = database[collection_name]
                prefix = f"{database.name}/{collection_name}"
                with archive.open(prefix + ".bson", "w", force_zip64=True) as output:
                    with collection.find().batch_size(100) as cursor:
                        for document in cursor:
                            output.write(BSON.encode(document))
                metadata = {
                    "options": info.get("options", {}),
                    "indexes": list(collection.list_indexes()),
                    "collectionName": collection_name,
                }
                archive.writestr(prefix + ".metadata.json", json_util.dumps(metadata))
        os.replace(temporary, directory / name)
    finally:
        Path(temporary).unlink(missing_ok=True)
