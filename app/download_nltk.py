import nltk

for resource in ('stopwords',):
    if not nltk.download(resource, raise_on_error=True):
        raise RuntimeError(f'Cannot download NLTK resource: {resource}')
