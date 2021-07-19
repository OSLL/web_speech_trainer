import i18n
from flask import Flask
    
def loadLocales(path: str):
    i18n.set('skip_locale_root_data', True)
    i18n.set('file_format', 'json')
    i18n.set('filename_format', '{locale}.{format}')
    i18n.load_path.append(path)

def changeLocale(locale: str, default: str = None):
    i18n.set('locale', locale)
    if(default):
        i18n.set('fallback', default)

def setupTemplatesAlias(app: Flask):
    app.jinja_env.globals.update(t= i18n.t)

def t(key, **kwargs):
    return i18n.t(key, kwargs=kwargs)
