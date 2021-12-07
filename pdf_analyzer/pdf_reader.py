import glob
import fitz


def get_first_strings(filename):
    with fitz.open(filename) as doc:
        titles = []
        for page in doc:
            titles.append(page.get_text().split('\n')[0])
    return titles


def get_list_with_files_names(directory_name, file_type):
    names_list = glob.glob(directory_name + "/*." + file_type)
    print("total pdf count = ", len(names_list))
    return names_list


def get_all_first_strings(directory_name, file_type):
    titles = []
    for name in get_list_with_files_names(directory_name, file_type):
        titles.extend(get_first_strings(name))

    return titles
