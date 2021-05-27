import argparse
import json
from collections import OrderedDict
from operator import itemgetter

from app.pdf_parser.slide_splitter import parse_pdf, text_processor
from app.pdf_parser.counters.base import BaseCounter


class BiGramCounter(BaseCounter):
    def __init__(self, text):
        super(BiGramCounter, self).__init__(text=text)
        self._compute_freq()

    def _compute_freq(self):
        text_list = self._text.split()
        text_len = len(text_list)

        for i in range(text_len):
            if i + 1 > text_len - 1:
                break
            item = ' '.join([text_list[i], text_list[i + 1]])
            self.add(item=item)

    @staticmethod
    def cmp_bi_grams(b1, b2, with_order=False):
        if with_order:
            b1_grams = set(b1.split())
            b2_grams = set(b2.split())
            return b1_grams == b2_grams
        else:
            return b1 == b2

    def save_as_json(self, filename, less_order=False):
        if not filename.endswith('.json'):
            filename = '%s.json' % filename

        if less_order:
            data = OrderedDict(sorted(self._items.items(), key=itemgetter(1), reverse=True))
        else:
            data = self._items

        with open(filename, 'w') as file:
            json.dump(data, file)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', action="store", dest="pdf")
    return parser.parse_args()


def main(args):
     bi_grams = BiGramCounter(text=text_processor(
         ' '.join(parse_pdf(args.pdf)),
         mode='pdf'))
     bi_grams.save_as_json(filename=args.pdf.rstrip('.pdf'), less_order=True)


if __name__ == "__main__":
    main(parse_args())
