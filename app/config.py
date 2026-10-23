"""Load Python settings while preserving Config.c.section.option access."""

import runpy
from pathlib import Path
from types import SimpleNamespace


class DictToObject(SimpleNamespace):
    def __init__(self, dictionary):
        super().__init__(
            **{
                key: DictToObject(value) if isinstance(value, dict) else value
                for key, value in dictionary.items()
            }
        )


class Config:
    c = None

    @staticmethod
    def init_config(config_path):
        if Config.c is not None:
            return
        path = Path(config_path)
        if path.suffix != ".py":
            raise ValueError("APP_CONF must point to a Python settings file")
        sections = {}
        for name, value in runpy.run_path(str(path)).items():
            if name.isupper() and "_" in name:
                normalized = name.lower()
                section, option = normalized.split("_", 1)
                for prefix in ("user_agent_platform", "user_agent_browser"):
                    if normalized.startswith(prefix + "_"):
                        section, option = prefix, normalized[len(prefix) + 1 :]
                        break
                sections.setdefault(section, {})[option] = value
        Config.c = DictToObject(sections)
