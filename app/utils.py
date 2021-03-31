import tempfile

import fitz
from pydub import AudioSegment

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
    temp_file = tempfile.NamedTemporaryFile()
    temp_file.write(presentation_file.read())
    pdf_doc = fitz.open(temp_file.name)
    start_page = pdf_doc.loadPage(0)
    pixmap = start_page.getPixmap()
    output_temp_file = tempfile.NamedTemporaryFile(delete=False)
    pixmap.writePNG(output_temp_file.name)
    return output_temp_file


