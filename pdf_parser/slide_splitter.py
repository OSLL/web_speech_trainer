import fitz
import pymorphy2

import os
import argparse


def extract_text_by_page(pdf_path, extract_dir):
    if not os.path.exists(extract_dir):
        os.mkdir(extract_dir)

    pdf_doc = fitz.open("example.pdf")

    for page in pdf_doc:
        text = page.getText("text")
        l_text = ''
        sentences = text.split('\n')
        morph = pymorphy2.MorphAnalyzer()

        for s in sentences:
            for word in s.split():
                l_text += morph.parse(word)[0].normal_form
                l_text += ' '
            l_text += '\n'

        with open("{}/{}_slide.txt".format(extract_dir, page.number), "w") as f:
            f.write(l_text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', action="store", dest="pdf")
    args = parser.parse_args()

    print(extract_text_by_page(args.pdf, args.pdf.split(".")[0]))

