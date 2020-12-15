import tempfile

from pydub import AudioSegment

PDF_HEX_START = ['25', '50', '44', '46']


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
