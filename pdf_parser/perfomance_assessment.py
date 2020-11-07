from text_comorator import base_cmp
from slide_splitter import parse_txt, parse_pdf

import argparse
import os


def check_headder(slide, opt):
    for headder in opt:
        if base_cmp(headder, slide[:len(headder)]) > 92:
            print("Пропускаем слайд с заголовком:", headder)
            return True

    return False


def perfomance_score(slide_dict, txt_dict, opt):
    print(opt)
    assessment = 0
    m = len(min(slide_dict, txt_dict))
    n = m

    for i in range(m):
        # Проверяем заголовки слайдов на совпадение с теми, что нужно пропустить
        if check_headder(slide_dict[i], opt):
            n -= 1
            continue
        assessment += base_cmp(slide_dict[i], txt_dict[i])

    return assessment / n


def txt_split(txt_path):
    with open(txt_path) as f:
        text = ''.join(f.readlines())
        return text.split("\n\n")


def pdf_split(pdf_dir):
    # Сортируем текст слайдов по возрастанию чтобы не напутать ничего при сравнении с выступлением
    files = sorted(os.listdir(pdf_dir), key=lambda x: int(x.split('_')[0]))
    slides = []

    for file in files:
        with open('{}/{}'.format(pdf_dir, file)) as f:
            slides.append(''.join(f.readlines()))

    return slides


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Путь к пдф
    parser.add_argument('--pdf', action="store", dest="pdf")

    # Путь к текстовому файлу выступления
    parser.add_argument('--txt', action="store", dest="txt")

    # Опция сравнения
    parser.add_argument('--opt', action="store", dest="opt", nargs='*', metavar='O')
    args = parser.parse_args()

    if args.pdf and args.txt:
        parse_pdf(args.pdf, args.pdf.split(".")[0])
        parse_txt(args.txt, args.txt.split(".")[0])
        print('Оценка выступлению:', perfomance_score(slide_dict=pdf_split(args.pdf.split(".")[0]),
                               txt_dict=txt_split('{}/clear.txt'.format(args.txt.split(".")[0])),
                               opt=args.opt),
              '%')


