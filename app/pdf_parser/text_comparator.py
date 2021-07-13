from fuzzywuzzy import fuzz
from nltk import word_tokenize, Text, download
from nltk.probability import FreqDist

from app.pdf_parser.counters.bi_gram import BiGrams

download('punkt')


def base_cmp(text1, text2):
    return fuzz.WRatio(text1, text2)


def value_slide_checking(slide_text):
    '''Проверяем есть ли в ОБРАБОТАНОМ тексте слайда ЗНАЧИМЫЕ слова

    :param slide_text:
    :return: bool
    '''
    # Начальные формы
    value_words = ["цель", "задача"]
    first_5 = ' '.join(slide_text.split()[:5])
    print(first_5)
    for w in value_words:
        if fuzz.partial_ratio(w, first_5) == 100:
            return True
    return False


def get_weight_scale(slide_text, transcript_text):
    '''Мы получаем частоту слов для обоих параметров, затем, в зависимости
    от совпадающих слов и их частот начисляем коэффициент, на который будут
    умножены результаты функции weight_cmp

    :param text1:
    :param text2:
    :return:
    '''
    slide_tokens1 = word_tokenize(slide_text)
    transcript_tokens2 = word_tokenize(transcript_text)
    tokenized_slide = Text(slide_tokens1)
    tokenized_transcript = Text(transcript_tokens2)
    slide_freq = FreqDist(tokenized_slide)
    transcript_freq = FreqDist(tokenized_transcript)

    slide_words = slide_freq.keys()
    transcript_words = transcript_freq.keys()

    n = len(transcript_words)
    k = 0
    count_value_words = 0

    for w in transcript_words:
        if w in slide_words:
            w_slide_freq = slide_freq[w]
            w_transcript_freq = min(transcript_freq[w], w_slide_freq)
            if w_slide_freq > 1:
                count_value_words += 1
                k += w_transcript_freq / n
                print("Слово: [%s]" % w)
                print('Trancript Freq:', transcript_freq[w])
                print('Slide Freq:', slide_freq[w])
                print('WEIGHT:', w_transcript_freq / n)
                print("Промежуточный аддитивный WEIGHT коэф. k =", k)
    print("Результирующий весовой коэффициент:", 1 + k/count_value_words)
    return (1 + k / count_value_words)


def get_bigram_weight_scale(slide_list, txt_list):
    pdf_text = ' '.join(slide_list).replace('\n', ' ')
    txt_text = ' '.join(txt_list).replace('\n', ' ')

    pdf_bigrams = BiGrams()
    pdf_bigrams.compute_freq(text=pdf_text)
    transcript_bigrams = BiGrams()
    transcript_bigrams.compute_freq(text=txt_text)

    transcript_freq = transcript_bigrams.freq_dict
    pdf_freq = pdf_bigrams.freq_dict

    n = len(transcript_freq)
    k = 0
    count_same_bi_grams = 0

    for pdf_bigram, pdf_bigram_freq in pdf_freq.items():
        if pdf_bigram in transcript_freq:
            min_freq = min(pdf_bigram_freq, transcript_freq[pdf_bigram])
            count_same_bi_grams += 1
            k += min_freq / n
            print("Биграмма: [%s]" % pdf_bigram)
            print('Trancript Freq:', transcript_freq[pdf_bigram])
            print('Pdf Freq:', pdf_freq)
            print('WEIGHT:', min_freq / n)
            print("Промежуточный аддитивный WEIGHT коэф. k =", k)
    print("Результирующий весовой коэффициент:", 1 + k / count_same_bi_grams)
    return (1 + k / count_same_bi_grams)


def weight_cmp(s1, s2, force_ascii=True, full_process=True):
    '''За основу взята функция fuzzywuzzy.fuzz.WRatio
    Ниже представлена моификация этой функции с учетом весого коэффициента

    :param text1:
    :param text2:
    :return:
    '''
    from fuzzywuzzy.fuzz import ratio, partial_ratio, partial_token_sort_ratio, \
        partial_token_set_ratio, token_sort_ratio, token_set_ratio
    from fuzzywuzzy import utils

    if full_process:
        p1 = utils.full_process(s1, force_ascii=force_ascii)
        p2 = utils.full_process(s2, force_ascii=force_ascii)
    else:
        p1 = s1
        p2 = s2

    if not utils.validate_string(p1):
        return 0
    if not utils.validate_string(p2):
        return 0

    # should we look at partials?
    try_partial = True
    unbase_scale = .95
    partial_scale = .90
    weight_scale = get_weight_scale(p1, p2) # Additional

    base = ratio(p1, p2)
    len_ratio = float(max(len(p1), len(p2))) / min(len(p1), len(p2))

    # if strings are similar length, don't use partials
    if len_ratio < 1.5:
        try_partial = False

    # if one string is much much shorter than the other
    if len_ratio > 8:
        partial_scale = .6

    if try_partial:
        partial = partial_ratio(p1, p2) * partial_scale
        ptsor = partial_token_sort_ratio(p1, p2, full_process=False) \
                * unbase_scale * partial_scale
        ptser = partial_token_set_ratio(p1, p2, full_process=False) \
                * unbase_scale * partial_scale
        res = utils.intr(max(base, partial, ptsor, ptser)) * weight_scale
        if res > 100:
            return 100
        return res
    else:
        tsor = token_sort_ratio(p1, p2, full_process=False) * unbase_scale
        tser = token_set_ratio(p1, p2, full_process=False) * unbase_scale
        res = utils.intr(max(base, tsor, tser)) * weight_scale
        if res > 100:
            return 100
        return res

