from app.presentation import Presentation
from app.recognized_presentation import RecognizedPresentation
from app.recognized_slide import RecognizedSlide


def test_presentation_split_into_slides():
    recognized_slides = [
        RecognizedSlide(words=['A', 'B', 'C']),
        RecognizedSlide(words=['D', 'E', 'F', 'G']),
        RecognizedSlide(words=['H', 'I', 'J', 'K', 'L', 'M'])
    ]
    recognized_presentation = RecognizedPresentation(recognized_slides)
    slide_switch_timestamps = [1, 2, 3, 4, 5]
    for i in range(0, 6):
        actual_presentation = Presentation(recognized_presentation, slide_switch_timestamps[:i])
        with open('test_data/presentation_{}.json'.format(i), 'rb') as presentation_file:
            expected_presentation = Presentation.from_json_file(presentation_file)
        assert actual_presentation == expected_presentation
