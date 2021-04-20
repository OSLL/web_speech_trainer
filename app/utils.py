import os
import tempfile
from distutils.util import strtobool

import fitz
from bson import ObjectId
from pydub import AudioSegment

from app.config import Config

PDF_HEX_START = ['25', '50', '44', '46']
SECONDS_PER_MINUTE = 60
BYTES_PER_MEGABYTE = 1024 * 1024


def file_has_pdf_beginning(file):
    for i in range(len(PDF_HEX_START)):
        if file.read(1).hex() != PDF_HEX_START[i]:
            file.seek(0)
            return False
    file.seek(0)
    return True


def convert_from_mp3_to_wav(audio, frame_rate=8000, channels=1):
    sound = AudioSegment.from_mp3(audio) \
        .set_frame_rate(frame_rate) \
        .set_channels(channels)
    temp_file = tempfile.NamedTemporaryFile()
    sound.export(temp_file.name, format="wav")
    return temp_file


def get_presentation_file_preview(presentation_file):
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(presentation_file.read())
    temp_file.close()
    pdf_doc = fitz.open(temp_file.name)
    os.remove(temp_file.name)
    start_page = pdf_doc.loadPage(0)
    pixmap = start_page.getPixmap()
    output_temp_file = tempfile.NamedTemporaryFile(delete=False)
    pixmap.writePNG(output_temp_file.name)
    return output_temp_file


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
    def wrapper(*args):
        for arg in args:
            check_argument_is_convertible_to_object_id(arg)
        return f(*args)
    return wrapper


def is_testing_active():
    try:
        return Config.c.testing.active
    except Exception:
        return False