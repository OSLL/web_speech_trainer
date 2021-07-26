import os
import tempfile
from distutils.util import strtobool
from threading import Timer

import fitz
from bson import ObjectId
import magic
from pydub import AudioSegment
import subprocess

from app.config import Config

PDF_HEX_START = ['25', '50', '44', '46']
SECONDS_PER_MINUTE = 60
BYTES_PER_MEGABYTE = 1024 * 1024
ALLOWED_MIMETYPES = {
        'pdf': 'application/pdf',
        'ppt': 'application/vnd.ms-powerpoint',
        'odp': 'application/vnd.oasis.opendocument.presentation',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }
CONVERTIBLE_EXTENSIONS = ('ppt', 'pptx', 'odp')


def file_has_pdf_beginning(file):
    for i in range(len(PDF_HEX_START)):
        if file.read(1).hex() != PDF_HEX_START[i]:
            file.seek(0)
            return False
    file.seek(0)
    return True


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

    file_mime = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)

    # also we can check, that file_mime is allowed, but not for expected_ext
    # (for example, pptx renamed to ppt) 
    return file_mime == ALLOWED_MIMETYPES[expected_ext], file_mime


def is_convertible(extension): return extension in CONVERTIBLE_EXTENSIONS


def convert_to_pdf(presentation_file):
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(presentation_file.read())
    temp_file.close()
    presentation_file.seek(0)
    
    converted_file = None
    convert_cmd = "unoconv -f pdf {}".format(temp_file.name)
    if run_process(convert_cmd).returncode == 0:
        # success conversion
        new_filename = "{}.pdf".format(temp_file.name)
        converted_file = open(new_filename, 'rb')
        os.remove(new_filename)

    os.remove(temp_file.name)
    return converted_file


def run_process(cmd: str): return subprocess.run(cmd.split(' '))


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
        return safe_strtobool(Config.c.testing.active)
    except Exception:
        return False


class RepeatedTimer:
    """
    Utility class to call a function with a given interval between the end and the beginning of consecutive calls
    """

    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.function(*self.args, **self.kwargs)
        self.start()

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False
