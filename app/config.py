import os
from configparser import ConfigParser
from collections import OrderedDict


class DictToObject(object):
    def __init__(self, dictionary):
        def _traverse(key, element):
            if isinstance(element, dict):
                return key, DictToObject(element)
            else:
                return key, element

        objd = OrderedDict(_traverse(k, v) for k, v in dictionary.items())
        self.__dict__.update(objd)


class Config:
    c = None

    @staticmethod
    def init_config(config_path):
        if Config.c:
            return
        config_raw = ConfigParser()
        config_raw.read(config_path)
        Config.c = DictToObject(config_raw._sections)

class VersionCache:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            hash_file = os.getenv("APP_STATIC_HASH_FILE", "dev")
            if hash_file and os.path.exists(hash_file):
                with open(hash_file) as f:
                    cls._instance.version=f.read().split()
            else:
                cls._instance.version = "dev"
            return cls._instance
    
    @classmethod
    def get_version(cls):
        return cls().version