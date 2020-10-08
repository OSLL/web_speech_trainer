import fitz

import os
import argparse


def extract_text_by_page(pdf_path, extract_dir):
    if not os.path.exists(extract_dir):
        os.mkdir(extract_dir)

    pdf_doc = fitz.open("example.pdf")

    for page in pdf_doc:
        text = page.getText("text")

        with open("{}/{}_slide.txt".format(extract_dir, page.number), "w") as f:
            f.write(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', action="store", dest="pdf")
    args = parser.parse_args()

    print(extract_text_by_page(args.pdf, args.pdf.split(".")[0]))

