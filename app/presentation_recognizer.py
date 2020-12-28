from app.mongo_odm import DBManager
from app.recognized_presentation import RecognizedPresentation
from app.recognized_slide import RecognizedSlide
from app.word import Word

import tempfile
from pdf_parser.slide_splitter import parse_pdf


class PresentationRecognizer:
    def recognize(self, presentation):
        pass


class SimplePresentationRecognizer:
    def recognize(self, presentation):
        print("Presetation:", presentation)
        tp = tempfile.NamedTemporaryFile()
        tp.write(presentation.file.read())
        print('Presentation name:', tp.name)
        slides = parse_pdf(pdf_path=tp.name, extract_dir=tp.name.split('/')[-1])
        recognized_slides = [RecognizedSlide(s) for s in slides]
        return RecognizedPresentation(recognized_slides)
