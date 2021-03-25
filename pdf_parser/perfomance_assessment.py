import argparse
import os

from text_comparator import base_cmp, weight_cmp, value_slide_checking

from slide_splitter import parse_txt, parse_pdf

from text_comparator import get_bigram_weight_scale


def check_headder(slide, opt):
    if opt is not None:
        for headder in opt:
            if base_cmp(headder, slide[:len(headder)]) > 92:
                print("Пропускаем слайд с заголовком:", headder)
                return True
    return False


def perfomance_score(slide_list, txt_list, opt, bi_grams_weight_scale=False):
    assessment = 0
    m = len(min(slide_list, txt_list))
    n = m
    print(m)
    for i in range(m):
        # Проверяем заголовки слайдов на совпадение с теми, что нужно пропустить
        if check_headder(slide_list[i], opt):
            n -= 1
            continue

        # Если есть "ЗНАЧИМЫЕ" слова, то проводим оценку слайда методом взвешивания
        if value_slide_checking(slide_list[i]):
            slide_assessment = weight_cmp(slide_list[i], txt_list[i])
            print("Оценка за взвешенный слайд %i - %i/100" % (i, slide_assessment))
        else:
            slide_assessment = base_cmp(slide_list[i], txt_list[i])
            print("Оценка за слайд %i - %i/100" % (i, slide_assessment))
        assessment += slide_assessment

    if bi_grams_weight_scale:
        return get_bigram_weight_scale() * assessment / n

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

    # Опция весового коэффициента биграмм
    parser.add_argument('--bg_weight', action='store', dest='bg_weight',
                        choices=['on', 'off'], default='off')

    args = parser.parse_args()

    if args.pdf and args.txt:
        parse_pdf(args.pdf, args.pdf.split(".")[0])
        parse_txt(args.txt, args.txt.split(".")[0])
        slide_list = pdf_split(args.pdf.split(".")[0])
        txt_list = txt_split('{}/clear.txt'.format(args.txt.split(".")[0]))

        score = perfomance_score(slide_list=pdf_split(args.pdf.split(".")[0]),
                                   txt_list=txt_split('{}/clear.txt'.format(args.txt.split(".")[0])),
                                   opt=args.opt)
        print('Оценка выступлению:', score, '%')

        if args.bg_weight == 'on':
            score *= get_bigram_weight_scale(slide_list=slide_list, txt_list=txt_list)
            if score > 100:
                score = 100
            print('Оценка выступлению с биграммами:', score, '%')


