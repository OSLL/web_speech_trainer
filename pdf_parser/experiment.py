import argparse
import json

from slide_splitter import parse_pdf, text_processor


class BiGrams:
    def compute_freq(self, pdf):
        self.freq_dict = {}
        slide_dict = parse_pdf(pdf_path=pdf)

        for slide in slide_dict:
            lemmas_slide = text_processor(text=slide, mode='pdf')
            text = lemmas_slide.split()
            text_len = len(text)
            for i in range(text_len):
                if i + 1 > text_len - 1:
                    break
                key = ' '.join([text[i], text[i + 1]])
                if key not in self.freq_dict:
                    self.freq_dict[key] = 1
                else:
                    self.freq_dict[key] += 1

    def save_as_json(self, filename):
        if not filename.endswith('.json'):
            filename = '%s.json' % filename
        with open(filename, 'w') as file:
            json.dump(self.freq_dict, file)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', action="store", dest="pdf")
    return parser.parse_args()


def main(args):
     bi_grams = BiGrams()
     bi_grams.compute_freq(pdf=args.pdf)
     bi_grams.save_as_json(filename=args.pdf.rstrip('.pdf'))


if __name__ == "__main__":
    main(parse_args())
