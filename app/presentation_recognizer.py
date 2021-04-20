import os
import tempfile

from pdf_parser.slide_splitter import parse_pdf

from app.recognized_presentation import RecognizedPresentation
from app.recognized_slide import RecognizedSlide


class PresentationRecognizer:
    def recognize(self, presentation):
        pass


class SimplePresentationRecognizer:
    def recognize(self, presentation):
        tp = tempfile.NamedTemporaryFile(delete=False)
        tp.write(presentation.read())
        tp.close()
        slides = parse_pdf(pdf_path=tp.name, extract_dir=tp.name.split('/')[-1])
        recognized_slides = [RecognizedSlide(s) for s in slides]
        os.remove(tp.name)
        return RecognizedPresentation(recognized_slides)
