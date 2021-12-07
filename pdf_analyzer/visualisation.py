import csv
import matplotlib.pyplot as plt
import numpy as np




def get_image(filename):
    names, values = get_data(filename)
    x = range(1, len(values) + 1)

    fig, ax = plt.subplots()
    bar = plt.bar(x, values, width=0.9, color=get_color_map(values))

    for idx, rect in enumerate(bar):
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., 15,
                names[idx],
                ha='center', va='bottom', rotation=90)


    plt.title('Most frequent words in title')
    ax.set_xlabel('Word')
    ax.set_ylabel('Frequency')
    # ax.set_yscale('log')
    ax.set_xticklabels([])

    fig.set_figwidth(15)  # ширина Figure
    fig.set_figheight(7)  # высота Figure

    plt.show()
#
# def get_image(filename):
#     names, values = get_data(filename)
#     x = range(1, len(values) + 1)
#
#     fig, ax = plt.subplots()
#
#     bar = ax.bar(x, values, width=0.9, color=get_color_map(values))
#
#     plt.title('Most frequent words in title')
#     ax.set_xlabel('Word')
#     ax.set_ylabel('Frequency')
#     # ax.set_yscale('log')
#     ax.set_xticklabels([])
#
#     fig.set_figwidth(15)  # ширина Figure
#     fig.set_figheight(7)  # высота Figure
#
#     plt.show()

    return "ready"


def get_color_map(values):
    rescale = lambda y: (y - np.min(y)) / (np.max(y) - np.min(y))
    my_cmap = plt.get_cmap("Wistia")
    return my_cmap(rescale(values))


def get_data(filename):
    data = dict()
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data[row['word']] = row['frequency']

    names = [str(key) for key in data.keys()]
    values = [int(num) for num in data.values()]

    return names, values
