import fitz
import os

from app.pdf_parser.data_processors.text_processor import TextProcessor


class PdfLoader:
    def load(self,
             file_path: str,
             process_text=True,
             extract_dir=None):
        self.__pdf_path = file_path
        self.__pdf_doc = fitz.open(file_path)

        self.slide_list = []
        self.processed_slide_list = []
        text_processor = TextProcessor()

        for page in self.__pdf_doc:
            text = page.getText("text")
            self.slide_list.append(text)

            if process_text:
                text_processor.process(text=text)
                self.processed_slide_list.append(text_processor.get_processed_text())
                text = text_processor.get_processed_text()

            if extract_dir is not None:
                if not os.path.exists(extract_dir):
                    os.mkdir(extract_dir)
                with open("{}/{}_slide.txt".format(extract_dir, page.number), "w") as f:
                    f.write(text)