import fitz
import pymorphy2
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords

import os
import argparse


def text_processor(text):
    l_text = ''
    sentences = text.split('\n')
    morph = pymorphy2.MorphAnalyzer()
    stop_words = stopwords.words('russian')

    # Лемматизация и удаление стоп слов
    for s in sentences:
        for word in s.split():
            normal_form = morph.parse(word)[0].normal_form
            if normal_form not in stop_words:
                l_text += normal_form
                l_text += ' '
            else:
                print('Удаляем шумовое слово:', normal_form)
        l_text += '\n'

    return l_text


def parse_txt(txt_path, extract_dir):
    if not os.path.exists(extract_dir):
        os.mkdir(extract_dir)

    with open(txt_path) as txt:
        text = txt.readlines()
        l_text = text_processor(''.join(text))

        with open('{}/clear.txt'.format(extract_dir), 'w') as f:
            f.write(l_text)


def parse_pdf(pdf_path, extract_dir):
    if not os.path.exists(extract_dir):
        os.mkdir(extract_dir)

    pdf_doc = fitz.open(pdf_path)

    for page in pdf_doc:
        text = page.getText("text")
        l_text = text_processor(text)

        with open("{}/{}_slide.txt".format(extract_dir, page.number), "w") as f:
            f.write(l_text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', action="store", dest="pdf")
    parser.add_argument('--txt', action="store", dest="txt")
    args = parser.parse_args()

    if args.pdf:
        parse_pdf(args.pdf, args.pdf.split(".")[0])
        print('Все готово... Результаты ждут вас в папке', args.pdf.split(".")[0])

    if args.txt:
        parse_txt(args.txt, args.txt.split(".")[0])
        print('Все готово... Результаты ждут вас в папке', args.txt.split(".")[0])




