from app.pdf_parser.assessments.slide_assessment import SlideAsessment

from app.pdf_parser.data_loaders.pdf_loader import PdfLoader
from app.pdf_parser.data_loaders.speech_transcript_loader import SpeechTranscriptLoader


class SpeechAssessment:
    def __init__(self,
                 pdf_path: str,
                 transcript_path: str):
        self.__pdf_path = pdf_path
        self.__transcript_path = transcript_path

        self.__pdf_loader = PdfLoader()
        self.__pdf_loader.load(file_path=self.__pdf_path)
        self.__speech_transcript_loader = SpeechTranscriptLoader()
        self.__speech_transcript_loader.load(file_path=self.__transcript_path)

    def make_on_words_with_cosine_assessment(self):
        self.slide_assessments = []
        slides = self.__pdf_loader.processed_slide_list
        corresponding_transcript_parts = self.__speech_transcript_loader.transcripts_processed_parts_list

        for slide_text, transcript_text in zip(slides, corresponding_transcript_parts):
            slide_assessment =\
                SlideAsessment().slide_assessment_on_words_with_cosine(slide_text=slide_text,
                                                                       transcript_text=transcript_text)
            print('Slide Assessment:', slide_assessment)
            self.slide_assessments.append(slide_assessment)

        self.average_assessment = sum(self.slide_assessments) / len(self.slide_assessments)


def main(args):
    pdf_path = args.pdf_path
    transcript_path = args.transcript_path

    speech_assessment = SpeechAssessment(pdf_path=pdf_path, transcript_path=transcript_path)
    speech_assessment.make_on_words_with_cosine_assessment()

    print('Speech Assessment:', speech_assessment.average_assessment)


