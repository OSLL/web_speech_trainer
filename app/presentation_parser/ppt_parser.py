from pptx import Presentation


def parse_ppt(presentation_filepath):
    presentation = Presentation(presentation_filepath)

    slides = []
    for slide in presentation.slides:
        slide = { 'title': slide.shapes.title.text if slide.shapes.title else '' }
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                slide['words'] += "\n" + shape.text
        slides.append(slide)
    return slides