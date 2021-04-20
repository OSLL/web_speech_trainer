import fitz
import pymorphy2
import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords

import os
import argparse
import re
import shutil


def text_processor(text, mode):
    # Очистка текста от англ слов и цифр
    text = re.sub(r'[^А-я\s]', '', text)

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
        l_text = l_text.strip(' ')
        l_text += '\n'

    if mode == "txt":
        l_text = re.sub(r'\n\n+', '\n\n', l_text)
    elif mode == "pdf":
        l_text = re.sub(r'\n+', '\n', l_text)

    return l_text


def parse_txt(txt_path, extract_dir):
    if not os.path.exists(extract_dir):
        os.mkdir(extract_dir)

    with open(txt_path) as txt:
        text = txt.readlines()
        l_text = text_processor(''.join(text), mode="txt")

        with open('{}/clear.txt'.format(extract_dir), 'w') as f:
            f.write(l_text)


def parse_pdf(pdf_path, extract_dir):
    '''Функция производит лемматизацию и очищение текста слайдов, сохраняет их в указанную папку

    :param pdf_path:
    :param extract_dir:
    :return: ['slide1 - full text', ..., 'slideN - full text]
    '''
    if not os.path.exists(extract_dir):
        os.mkdir(extract_dir)

    pdf_doc = fitz.open(pdf_path)
    slide_dict = []

    for page in pdf_doc:
        text = page.getText("text")
        slide_dict.append(text)
        l_text = text_processor(text, mode="pdf")

        with open("{}/{}_slide.txt".format(extract_dir, page.number), "w") as f:
            f.write(l_text)
    shutil.rmtree(extract_dir, ignore_errors=True)
    return slide_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', action="store", dest="pdf")
    parser.add_argument('--txt', action="store", dest="txt")
    parser.add_argument('--mrg_txt', action="store", dest="mrg_txt")
    args = parser.parse_args()

    if args.pdf:
        print(parse_pdf(args.pdf, args.pdf.split(".")[0]))
        print('Все готово... Результаты ждут вас в папке', args.pdf.split(".")[0])

    if args.txt:
        parse_txt(args.txt, args.txt.split(".")[0])
        print('Все готово... Результаты ждут вас в папке', args.txt.split(".")[0])

    if args.mrg_txt:
        from file_merger import file_merger
        file_merger(args.mrg_txt)




