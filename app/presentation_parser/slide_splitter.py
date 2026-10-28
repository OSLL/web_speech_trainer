"""Extract slide text from PDF without intermediate files."""
import fitz


def parse_pdf(pdf_path):
    with fitz.open(pdf_path) as document:
        return [page.get_text("text") for page in document]
