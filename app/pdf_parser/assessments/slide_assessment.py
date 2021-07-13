from app.pdf_parser.text_comporators.on_word_counters import TextComporatorOnWordCounter
from app.pdf_parser.text_comporators.on_bi_gram_counter import TextComporatorOnBiGramCounter

from app.pdf_parser.data_processors.text_processor import TextProcessor


class SlideAsessment:
    def __init__(self):
        pass

    def slide_assessment_on_words_with_cosine(self,
                                              slide_text,
                                              transcript_text,
                                              preprocess_text=False):
        if preprocess_text:
            text_processor = TextProcessor()
            text_processor.process(text=slide_text)
            slide_text = text_processor.get_processed_text()
            text_processor.process(text=transcript_text)
            transcript_text = text_processor.get_processed_text()

        self.__on_words_comporator = TextComporatorOnWordCounter()
        self.__on_words_assessment = self.__on_words_comporator.cosine_compare(
            text1=slide_text,
            text2=transcript_text,
            get_text1_as_sample=True
        )
        meta = self.__on_words_comporator.get_meta()
        #print('Slide Weights:', meta.text1_token_weights)
        #print('Transcripts Weights:', meta.text2_token_weights)
        return self.__on_words_assessment

    def slide_assessment_on_bigram_with_cosine(self,
                                              slide_text,
                                              transcript_text,
                                              preprocess_text=False):
        if preprocess_text:
            text_processor = TextProcessor()
            text_processor.process(text=slide_text)
            slide_text = text_processor.get_processed_text()
            text_processor.process(text=transcript_text)
            transcript_text = text_processor.get_processed_text()

        self.__on_words_comporator = TextComporatorOnBiGramCounter()
        self.__on_words_assessment = self.__on_words_comporator.cosine_compare(
            text1=slide_text,
            text2=transcript_text,
            get_text1_as_sample=True
        )
        meta = self.__on_words_comporator.get_meta()
        #print('Slide Weights:', meta.text1_token_weights)
        #print('Transcripts Weights:', meta.text2_token_weights)
        return self.__on_words_assessment


def main(args):
    slide_text_path = args.slide_text_file
    transcript_text_path = args.transcript_part_text_file

    with open(slide_text_path, 'r') as f:
        slide_text = f.read()

    with open(transcript_text_path, 'r') as f:
        transcript_text = f.read()

    slide_assessment = SlideAsessment()
    assessment = slide_assessment.slide_assessment_on_bigram_with_cosine(
        slide_text=slide_text,
        transcript_text=transcript_text,
        preprocess_text=True
    )
    print('Slide Assessment:', assessment * 100, '%')
