from fuzzywuzzy import fuzz
from nltk import word_tokenize, Text, download
from nltk.probability import FreqDist

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


def get_weight_scale(text1, text2):
    '''Мы получаем частоту слов для обоих параметров, затем, в зависимости
    от совпадающих слов и их частот начисляем коэффициент, на который будут
    умножены результаты функции weight_cmp

    :param text1:
    :param text2:
    :return:
    '''
    text_tokens1 = word_tokenize(text1)
    text_tokens2 = word_tokenize(text2)
    t1 = Text(text_tokens1)
    t2 = Text(text_tokens2)
    fdist1 = FreqDist(t1)
    fdist2 = FreqDist(t2)

    words1 = fdist1.keys()
    words2 = fdist2.keys()
    print(words1)
    print(words2)
    n = max(len(words1), len(words2))
    k = 0
    count_value_words = 0

    for w in words1:
        if w in words2:
            m = max(fdist1[w], fdist2[w])
            if m > 1:
                count_value_words += 1
                k += m / n
                print("Слово", w)
                print("Промежуточный коэф. k =", k)
    print("Результирующий весовой коэффициент:", 1 + k/count_value_words)
    return (1 + k / count_value_words)


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

