import pandas


def _safe_attr(obj, attr):
    try:
        return getattr(obj, attr)
    except (ValueError, TypeError):
        return None


class Paragraph:

    def __init__(self, paragraph):
        self.paragraph_text = paragraph.text
        self.paragraph_style_name = paragraph.style.name
        fmt = paragraph.paragraph_format
        self.paragraph_alignment = _safe_attr(fmt, 'alignment')
        self.paragraph_left_indent = _safe_attr(fmt, 'left_indent')
        self.paragraph_right_indent = _safe_attr(fmt, 'right_indent')
        self.paragraph_first_line_indent = _safe_attr(fmt, 'first_line_indent')
        self.paragraph_space_after = _safe_attr(fmt, 'space_after')
        self.paragraph_space_before = _safe_attr(fmt, 'space_before')
        self.paragraph_line_spacing = _safe_attr(fmt, 'line_spacing')
        self.paragraph_line_spacing_rule = _safe_attr(fmt, 'line_spacing_rule')
        self.paragraph_keep_together = _safe_attr(fmt, 'keep_together')
        self.paragraph_keep_with_next = _safe_attr(fmt, 'keep_with_next')
        self.paragraph_page_break_before = _safe_attr(fmt, 'page_break_before')
        self.paragraph_widow_control = _safe_attr(fmt, 'widow_control')
        self.modify()

    def to_string(self):
        df = pandas.DataFrame({'Values': [self.paragraph_text, self.paragraph_alignment, self.paragraph_left_indent,
                                          self.paragraph_right_indent, self.paragraph_first_line_indent,
                                          self.paragraph_space_after, self.paragraph_space_before,
                                          self.paragraph_line_spacing, self.paragraph_line_spacing_rule,
                                          self.paragraph_keep_together, self.paragraph_keep_with_next,
                                          self.paragraph_page_break_before, self.paragraph_widow_control]})
        df.index = ['TEXT', 'ALIGNMENT', 'LEFT_INDENT', 'RIGHT_INDENT', 'FIRST_LINE_INDENT', 'SPACE_AFTER',
                    'SPACE_BEFORE', 'LINE_SPACING', 'LINE_SPACING_RULE', 'KEEP_TOGETHER', 'KEEP_WITH_NEXT',
                    'PAGE_BREAK_BEFORE', 'WIDOW_CONTROL']
        return df.to_string()

    def modify(self):
        if self.paragraph_left_indent is not None:
            self.paragraph_left_indent = self.paragraph_left_indent.cm
        if self.paragraph_right_indent is not None:
            self.paragraph_right_indent = self.paragraph_right_indent.cm
        if self.paragraph_first_line_indent is not None:
            self.paragraph_first_line_indent = self.paragraph_first_line_indent.cm
        if self.paragraph_space_after is not None:
            self.paragraph_space_after = self.paragraph_space_after.pt
        if self.paragraph_space_before is not None:
            self.paragraph_space_before = self.paragraph_space_before.pt
