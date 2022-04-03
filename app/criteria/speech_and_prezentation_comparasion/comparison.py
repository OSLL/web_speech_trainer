def estimate_by_intersection(main_text, general_text):
    if not isinstance(main_text, set):
        main_text = set(main_text)

    if not isinstance(general_text, set):
        general_text = set(general_text)

    coincidence = len(main_text.intersection(general_text))

    return 0 if len(main_text) == 0 else coincidence / len(main_text)