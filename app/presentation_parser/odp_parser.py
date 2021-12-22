from odf import opendocument, draw


def parse_odp(presentation_filepath):
    presentation = opendocument.load(presentation_filepath)

    slides = []
    for slide in presentation.getElementsByType(draw.Page):
        slide_info = {'title': '', 'words': ''}

        title = []
        texts = []
        for node in slide.childNodes:
            if _is_title(node):
                _walk_children(node, title)
            else:
                node_text = []
                _walk_children(node, node_text)
                texts.append(node_text)

        slide_info['title'] = "\n".join(title)
        for text in texts:
            slide_info['words'] += " ".join(text) + "\n"
        slides.append(slide_info)
    return slides


def _is_title(node):
    for tuple_key in node.attributes:
        if tuple_key[1] == 'class':
            return node.attributes[tuple_key] == "title"


def _walk_children(child, child_container):
    if hasattr(child, "data"):
        child_container.append(child.data)
    else:
        for in_child in child.childNodes:
            _walk_children(in_child, child_container)
