import os


def file_merger(dir):
    files = os.listdir(dir)
    full_text = ''

    for file in files:
        with open('{}/{}'.format(dir,file)) as f:
            full_text += ''.join(f.readlines())

    with open('{}_merge.txt'.format(dir), 'w') as f:
        f.write(full_text)

    return full_text