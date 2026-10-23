import os
import tempfile

from app.recognized_presentation import RecognizedPresentation
from app.recognized_slide import RecognizedSlide
from presentation_parser.odp_parser import parse_odp
from presentation_parser.ppt_parser import parse_ppt
from presentation_parser.slide_splitter import parse_pdf


class PresentationRecognizer:

    def recognize(self, presentation):
        path = self.save_to_tmp(presentation)
        try:
            return self.process_slides(self.parse_presentation(path))
        finally:
            os.remove(path)

    def save_to_tmp(self, presentation):
        tp = tempfile.NamedTemporaryFile(delete=False)
        tp.write(presentation.read())
        tp.close()
        return tp.name

    def parse_presentation(self, path):
        raise NotImplementedError()

    def process_slides(self, slides):
        raise NotImplementedError()


class SimplePDFPresentationRecognizer(PresentationRecognizer):

    def parse_presentation(self, path):
        return parse_pdf(path)

    def process_slides(self, slides):
        return RecognizedPresentation([RecognizedSlide(s) for s in slides])


class SimplePPTPresentationRecognizer(PresentationRecognizer):

    def parse_presentation(self, path):
        return parse_ppt(path)

    def process_slides(self, slides):
        return RecognizedPresentation([RecognizedSlide(**s) for s in slides])


class SimpleODPPresentationRecognizer(PresentationRecognizer):
    
    def parse_presentation(self, path):
        return parse_odp(path)

    def process_slides(self, slides):
        return RecognizedPresentation([RecognizedSlide(**s) for s in slides])


PRESENTATION_RECOGNIZERS = {
    'pdf': SimplePDFPresentationRecognizer(),
    'odp': SimpleODPPresentationRecognizer(),
    'ppt': SimplePPTPresentationRecognizer(),
    'pptx': SimplePPTPresentationRecognizer(),
}