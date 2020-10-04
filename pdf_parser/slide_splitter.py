import io
import os
import argparse

from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage


def extract_text_by_page(pdf_path, extract_dir):
    if not os.path.exists(extract_dir):
        os.mkdir(extract_dir)

    with open(pdf_path, 'rb') as fh:
         page_num = 0
         for page in PDFPage.get_pages(fh,
                                  caching=True,
                                  check_extractable=True):
            resource_manager = PDFResourceManager()
            fake_file_handle = io.StringIO()
            converter = TextConverter(resource_manager, fake_file_handle)
            page_interpreter = PDFPageInterpreter(resource_manager, converter)
            page_interpreter.process_page(page)

            text = fake_file_handle.getvalue()
            page_num += 1

            with open("{}/{}_slide.txt".format(extract_dir, page_num), "w") as f:
                f.write(text)

            # close open handles
            converter.close()
            fake_file_handle.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', action="store", dest="pdf")
    args = parser.parse_args()

    print(extract_text_by_page(args.pdf, args.pdf.split(".")[0]))

