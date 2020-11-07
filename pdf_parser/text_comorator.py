from fuzzywuzzy import fuzz


def base_cmp(text1, text2):
    return fuzz.WRatio(text1, text2)