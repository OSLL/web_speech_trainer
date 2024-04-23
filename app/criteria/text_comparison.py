from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import Word2Vec
from nltk.tokenize import word_tokenize
from nltk.util import ngrams
from collections import Counter


def tfidf_similarity(current_slide_speech: str, current_slide_text: str) -> float:
    corpus = [current_slide_speech, current_slide_text]
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(corpus)
    cosine_sim = cosine_similarity(X[0], X[1])
    similarity = cosine_sim[0][0]
    return round(similarity, 3)


def word2vec_similarity(current_slide_speech: str, current_slide_text: str) -> float:
    tokens_speech = word_tokenize(current_slide_speech)
    tokens_slide = word_tokenize(current_slide_text)
    sentences = [tokens_speech, tokens_slide]
    model = Word2Vec(sentences, min_count=1)
    similarity = model.wv.n_similarity(tokens_speech, tokens_slide)
    return round(similarity, 3)


def n_gramms_similarity(current_slide_speech: str, current_slide_text: str, n_values: list, weights: list) -> float:
    get_ngrams = lambda text, n: [' '.join(gram) for gram in ngrams(word_tokenize(text.lower()), n)]
    similarities = []
    for n in n_values:
        ngrams_text1 = get_ngrams(current_slide_speech, n)
        ngrams_text2 = get_ngrams(current_slide_text, n)

        counter_text1 = Counter(ngrams_text1)
        counter_text2 = Counter(ngrams_text2)

        intersection = set(ngrams_text1) & set(ngrams_text2)

        if len(ngrams_text1) == 0 or len(ngrams_text2) == 0:
            similarities.append(0.000)
        else:
            similarity = sum(
                min(counter_text1[ngram], counter_text2[ngram]) for ngram in intersection) / max(
                len(ngrams_text1), len(ngrams_text2))
            similarities.append(similarity)

    if weights:
        combined_similarity = sum(
            weight * similarity for weight, similarity in zip(weights, similarities))
    else:
        combined_similarity = sum(similarities) / len(similarities)

    return round(combined_similarity, 3)
