import argparse
import json
from collections import OrderedDict
from operator import itemgetter

from .slide_splitter import parse_pdf, text_processor


class BiGrams:
    def compute_freq(self, text):
        freq_dict = {}
        text_list = text.split()

        text_len = len(text_list)
        for i in range(text_len):
            if i + 1 > text_len - 1:
                break
            key = ' '.join([text_list[i], text_list[i + 1]])
            if key not in freq_dict:
                freq_dict[key] = 1
            else:
                freq_dict[key] += 1
        self.freq_dict = {bi_gram: freq for bi_gram, freq in freq_dict.items() if freq > 1}

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
            data = OrderedDict(sorted(self.freq_dict.items(), key=itemgetter(1), reverse=True))
        else:
            data = self.freq_dict

        with open(filename, 'w') as file:
            json.dump(data, file)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', action="store", dest="pdf")
    return parser.parse_args()


def main(args):
     bi_grams = BiGrams()
     bi_grams.compute_freq(text=text_processor(
         ' '.join(parse_pdf(args.pdf)),
         mode='pdf'))
     bi_grams.save_as_json(filename=args.pdf.rstrip('.pdf'), less_order=True)


if __name__ == "__main__":
    main(parse_args())
