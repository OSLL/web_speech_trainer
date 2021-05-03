import argparse
import os

from text_comparator import base_cmp, weight_cmp, value_slide_checking

from slide_splitter import parse_txt, parse_pdf

from text_comparator import get_bigram_weight_scale


def check_headder(slide, opt):
    for headder in opt:
        if base_cmp(headder, slide[:len(headder)]) > 92:
            print("Пропускаем слайд с заголовком:", headder)
            return True
    return False


def perfomance_score(pdf_path, txt_path, pass_slide_headers, word_weight_scale=False, bi_grams_weight_scale=False):
    slide_list = parse_pdf(pdf_path=pdf_path, ret_lematize_slides=True)
    txt_list = parse_txt(txt_path=txt_path)

    assessment = 0
    m = min(len(slide_list), len(txt_list))
    n = m
    print(m)
    for i in range(m):
        #print('Номер:', i)
        #print('Processed slide text:\n', slide_list[i])
        #print('Processed speech part:\n', txt_list[i])
        # Проверяем заголовки слайдов на совпадение с теми, что нужно пропустить
        if check_headder(slide_list[i], pass_slide_headers):
            n -= 1
            continue

        # Если есть "ЗНАЧИМЫЕ" слова, то проводим оценку слайда методом взвешивания
        if word_weight_scale and value_slide_checking(slide_list[i]):
            slide_assessment = weight_cmp(slide_list[i], txt_list[i])
            print("Оценка за взвешенный слайд %i - %i/100" % (i, slide_assessment))
        else:
            slide_assessment = base_cmp(slide_list[i], txt_list[i])
            print("Оценка за слайд %i - %i/100" % (i, slide_assessment))
        assessment += slide_assessment

    if bi_grams_weight_scale:
        assessment *= get_bigram_weight_scale(slide_list=slide_list, txt_list=txt_list)

    total_assessment = assessment / n

    if total_assessment > 100:
        total_assessment = 100

    return total_assessment


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Путь к пдф
    parser.add_argument('--pdf', action="store", dest="pdf")

    # Путь к текстовому файлу выступления
    parser.add_argument('--txt', action="store", dest="txt")

    # Список заголовков слайдов, которые нужно пропустить
    parser.add_argument('--pass_slide_headers', action="store", dest="pass_slide_headers",
                        nargs='*', metavar='O', default=[])

    # Опция весового коэффициента "значимых" слов для слайдов Цели, Задачи
    parser.add_argument('--word_weight', action='store', dest='word_weight',
                        choices=['on', 'off'], default='off')

    # Опция весового коэффициента биграмм
    parser.add_argument('--bg_weight', action='store', dest='bg_weight',
                        choices=['on', 'off'], default='off')

    args = parser.parse_args()
    word_weight = True if args.word_weight == 'on' else False
    bg_weight = True if args.bg_weight == 'on' else False

    if args.pdf and args.txt:
        score = perfomance_score(pdf_path=args.pdf,
                                 txt_path=args.txt,
                                 pass_slide_headers=args.pass_slide_headers,
                                 word_weight_scale=word_weight,
                                 bi_grams_weight_scale=bg_weight
        )
        print('Оценка выступлению:', score, '%')


