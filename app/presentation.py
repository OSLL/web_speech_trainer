import json

from app.slide import Slide


class Presentation:
    def __init__(self, recognized_presentation=None, slide_switch_timestamps=None):
        if recognized_presentation is None or slide_switch_timestamps is None:
            self.slides = None
            self.presentation_stats = None
        else:
            self.slides = self.split_into_slides(recognized_presentation, slide_switch_timestamps)
            self.presentation_stats = self.calculate_presentation_stats(
                recognized_presentation,
                slide_switch_timestamps,
            )

    def split_into_slides(self, recognized_presentation, slide_switch_timestamps):
        slides = []
        for i in range(len(recognized_presentation.recognized_slides)):
            slides.append(Slide(
                recognized_presentation.recognized_slides[i].words,
                slide_stats={
                    'begin_timestamp': slide_switch_timestamps[i],
                    'end_timestamp': slide_switch_timestamps[i + 1],
                    'slide_number': i,
                },
            ))
        return slides

    def calculate_presentation_stats(self, recognized_presentation, slide_switch_timestamps):
        if len(self.slides) == 0:
            duration = 0
        else:
            duration = self.slides[-1].slide_stats['end_timestamp'] - self.slides[0].slide_stats['begin_timestamp']
        return {
            'duration': duration
        }

    def __repr__(self):
        return json.dumps({
            'slides': [repr(slide) for slide in self.slides],
            'presentation_stats': json.dumps(self.presentation_stats),
        })

    @staticmethod
    def from_json_file(json_file):
        '''
        import sys
        with open('tmp.txt', 'wb+') as file:
            json_file.gridfs.download_to_stream(json_file.file_id, file)
        '''
        presentation = Presentation()
        json_obj = json.load(json_file)
        json_slides = json_obj['slides']
        presentation.slides = [Slide.from_json_string(json_slide) for json_slide in json_slides]
        presentation.presentation_stats = json.loads(json_obj['presentation_stats'])
        return presentation
