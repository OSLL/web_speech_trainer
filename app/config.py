from configparser import ConfigParser
from collections import OrderedDict


class DictToObject(object):
    def __init__(self, dictionary):
        def _traverse(key, element):
            if isinstance(element, OrderedDict):
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


if __name__ == "__main__":
    Config.init_config('config.ini')