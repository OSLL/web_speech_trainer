import operator
import pdf_reader
import words_parser


def construct_titles_dict(directory_name):
    all_first_strings = pdf_reader.get_all_first_strings(directory_name, "pdf")
    print("total pages count = ", len(all_first_strings))
    parsed_titles = parse_titles_to_dict(all_first_strings)

    return sort(parsed_titles)


def parse_titles_to_dict(first_strings):
    titles = dict()
    for first_string in first_strings:
        parsed = words_parser.parse(first_string, tags={'NOUN', 'VERB', 'INFN'})
        for word in parsed:
            if word in titles:
                titles[word] += 1
            else:
                titles[word] = 1
    return titles


def sort(dict_for_sorting):
    sorted_tuples = sorted(dict_for_sorting.items(), key=operator.itemgetter(1))
    return {k: v for k, v in sorted_tuples}


def get_most_recent(data, total_count=- 1, lower_bound=0):

    if total_count < 1 and lower_bound < 1:
        return data

    sorted_tuples = sorted(data.items(), key=operator.itemgetter(1))

    if total_count > 0:
        return {k: v for k, v in sorted_tuples[len(sorted_tuples) - total_count:]}
    elif lower_bound > 0:
        return {k: v for k, v in sorted_tuples if v > lower_bound}
