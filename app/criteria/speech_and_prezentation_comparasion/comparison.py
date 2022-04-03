def estimate_by_intersection(main_text, general_text):
    if not isinstance(main_text, set):
        main_text = set(main_text)

    if not isinstance(general_text, set):
        general_text = set(general_text)

    concurrence = len(main_text & general_text)

    return 0 if len(main_text) == 0 else concurrence / len(main_text)


def estimate_by_comparing_keywords(main_text, general_text_keywords, general_text_all):
    if not isinstance(main_text, set):
        main_text = set(main_text)
    if not isinstance(main_text, set):
        general_text_keywords = set(general_text_keywords)
    general_text_add = set(general_text_all).difference(general_text_keywords)

    concurrence = len(main_text & general_text_keywords)
    difference = len(main_text & general_text_add)

    return 0 if concurrence == 0 else concurrence / (concurrence + difference)
