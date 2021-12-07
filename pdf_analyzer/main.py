import title_getter
import csv

import visualisation


def write_dict_to_csv(data_in_dict, result_file_name):
    header = ['word', 'frequency']
    with open('result.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for k, v in data_in_dict.items():
            writer.writerow([k, v])


def write_frequent_titles_to_csv(data_in_dict):
    count = 30
    most_recent = title_getter.get_most_recent(data_in_dict, total_count=count)
    write_dict_to_csv(most_recent, "result.csv")


def write_all_title_words_to_csv(data_in_dict):
    write_dict_to_csv(data_in_dict, "all_words.csv")


def update_results():
    print('start processing...')

    data = title_getter.construct_titles_dict("clean presentations")

    write_all_title_words_to_csv(data)
    print("getting titles is finished. Start sorting... ")

    write_dict_to_csv(data)
    print('csv is ready')


if __name__ == '__main__':
    # update_results()
    print(visualisation.get_image("result.csv"))