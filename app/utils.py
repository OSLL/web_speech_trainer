import string
import re
import tempfile

import fitz
from bson import ObjectId
from flask import json, url_for, current_app
import magic
import pymorphy3
from nltk.corpus import stopwords
from pydub import AudioSegment
import subprocess
from app.config import Config
import hashlib
from pathlib import Path

SECONDS_PER_MINUTE = 60
BYTES_PER_MEGABYTE = 1024 * 1024
ALLOWED_MIMETYPES = {
    'pdf': ['application/pdf'],
    'ppt': ['application/vnd.ms-powerpoint'],
    'odp': ['application/vnd.oasis.opendocument.presentation'],
    'pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/zip']
}
CONVERTIBLE_EXTENSIONS = ('ppt', 'pptx', 'odp')
ALLOWED_EXTENSIONS = set(ALLOWED_MIMETYPES.keys())
DEFAULT_EXTENSION = 'pdf'


def strtobool(value):
    value = str(value).lower()
    if value in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    if value in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    raise ValueError('Invalid boolean value')


def check_file_mime(file, expected_ext):
    """
    : file: file-object
    : expected_ext: str, expected file extension (pdf, pptx, odp)
    return: Tuple(check_result, file_mime)
        - check_result
            - False, if expected_ext isn't allowed or file_mime != expected_ext
        - file_mime
            - None, if expected_ext isn't allowed
    """
    # TODO: add params for user-allowed extensions (#250)
    if expected_ext not in ALLOWED_MIMETYPES:
        return False, None

    file_mime = get_file_mime(file)

    # also we can check, that file_mime is allowed, but not for expected_ext
    # (for example, pptx renamed to ppt) 
    return file_mime in ALLOWED_MIMETYPES[expected_ext], file_mime


def get_file_mime(file):
    """
    : file: file-object
    return: file_mime (from magic)
    """
    file_mime = magic.from_buffer(file.read(), mime=True)
    file.seek(0)
    return file_mime


def is_convertible(extension): return extension in CONVERTIBLE_EXTENSIONS


def convert_to_pdf(presentation_file):
    from io import BytesIO
    with tempfile.TemporaryDirectory(prefix='wst-convert-') as directory:
        suffix = Path(presentation_file.filename).suffix.lower()
        source = Path(directory) / ('presentation' + suffix)
        source.write_bytes(presentation_file.read())
        presentation_file.seek(0)
        result = subprocess.run(['soffice', '-env:UserInstallation=file://' + directory + '/profile',
                                 '--headless', '--convert-to', 'pdf', '--outdir', directory, str(source)],
                                capture_output=True, timeout=120)
        output = source.with_suffix('.pdf')
        if result.returncode or not output.is_file():
            return None
        return BytesIO(output.read_bytes())


def convert_from_mp3_to_wav(audio, frame_rate=8000, channels=1):
    sound = AudioSegment.from_mp3(audio) \
        .set_frame_rate(frame_rate) \
        .set_channels(channels)
    temp_file = tempfile.NamedTemporaryFile()
    sound.export(temp_file.name, format="wav")
    return temp_file


def get_presentation_file_preview(presentation_file):
    with fitz.open(stream=presentation_file.read(), filetype='pdf') as document:
        if not len(document):
            raise ValueError('Presentation contains no pages')
        output = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        document[0].get_pixmap().save(output.name)
        return output


def safe_strtobool(value, on_error=False):
    if isinstance(value, bool):
        return value
    try:
        return bool(strtobool(value))
    except ValueError:
        return on_error


def remove_blank_and_none(d):
    for (key, value) in d.copy().items():
        if not value:
            d.pop(key)
    return d


def check_argument_is_convertible_to_object_id(arg):
    try:
        ObjectId(arg)
    except Exception as e1:
        try:
            return {'message': '{} cannot be converted to ObjectId. {}: {}'.format(arg, e1.__class__, e1)}, 404
        except Exception as e2:
            return {
                'message': 'Some arguments cannot be converted to ObjectId or to str. {}: {}.'
                .format(e2.__class__, e2)
            }, 404


def check_arguments_are_convertible_to_object_id(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        for arg in (*args, *kwargs.values()):
            error = check_argument_is_convertible_to_object_id(arg)
            if error:
                return error
        return f(*args, **kwargs)
    return wrapper


def is_testing_active():
    try:
        return safe_strtobool(Config.c.testing.active)
    except Exception:
        return False




def try_load_json(json_string):
    try:
        return json.loads(json_string), ''
    except Exception as exc:
        return None, str(exc)


def check_dict_keys(dictionary, keys):
    msg = ''
    for key in keys:
        if key not in dictionary:
            msg += f"No '{key}' in dictionary.\n"
    return f"{msg}\n{dictionary}" if msg else ''


# Функция нормализации текста
def normalize_text(text: list) -> list:
    table = str.maketrans("", "", string.punctuation)
    morph = pymorphy3.MorphAnalyzer()

    # Замена знаков препинания на пустые строки, конвертация в нижний регистр и обрезание пробелов по краям
    text = list(map(lambda x: x.translate(table).lower().strip(), text))
    # Замена цифр и слов не на русском языке на пустые строки
    text = list(map(lambda x: re.sub(r'[^А-яёЁ\s]', '', x), text))
    # Удаление пустых строк
    text = list(filter(lambda x: x.isalpha(), text))
    # Приведение слов к нормальной форме
    text = list(map(lambda x: morph.normal_forms(x)[0], text))
    # Очистка от стоп-слов
    text = list(filter(lambda x: x not in RussianStopwords().words, text))
    return text


# Удаление пунктуации из текста
def delete_punctuation(text: str) -> str:
    return text.translate(str.maketrans('', '', string.punctuation + "\t\n\r\v\f"))


def calc_static_hash(static_dir):
    md5 = hashlib.md5()
    for path in sorted(Path(static_dir).rglob("*")):
        if path.is_file():
            md5.update(path.read_bytes())
    return md5.hexdigest()


def versioned_url(filename):
    v = current_app.config["STATIC_VERSION"]
    if not v:
        return url_for("static", filename=filename)
    return url_for("static", filename=filename, v=v)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class RussianStopwords(metaclass=Singleton):

    def __init__(self):
        self.words = stopwords.words('russian')
