from app.pdf_parser.counters.base import BaseCounter


class WordCounter(BaseCounter):
    def __init__(self, text):
        super(WordCounter, self).__init__(text=text)
        self._compute_freq()

    def _compute_freq(self):
        text_list = self._text.split()
        text_len = len(text_list)

        for i in range(text_len):
            item = text_list[i]
            self.add(item=item)