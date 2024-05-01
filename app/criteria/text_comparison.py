from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models.doc2vec import Doc2Vec, TaggedDocument


class SlidesSimilarityEvaluator:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 1))

    def train_model(self, corpus: list):
        self.vectorizer.fit(corpus)

    def evaluate_semantic_similarity(self, text1: str, text2: str) -> float:
        vector1 = self.vectorizer.transform([text1])
        vector2 = self.vectorizer.transform([text2])
        similarity = cosine_similarity(vector1, vector2)[0][0]

        return round(similarity, 3)


class Doc2VecEvaluator:
    def __init__(self, vector_size: int, window: int, min_count: int, workers: int, epochs: int, dm: int):
        self.model = Doc2Vec(vector_size=vector_size, window=window, min_count=min_count, workers=workers,
                             epochs=epochs, dm=dm)

    def train_model(self, documents: list):
        tagged_documents = [TaggedDocument(words=doc.split(), tags=[i]) for i, doc in enumerate(documents)]
        self.model.build_vocab(tagged_documents)
        self.model.train(tagged_documents, total_examples=self.model.corpus_count, epochs=self.model.epochs)

    def evaluate_semantic_similarity(self, text1: str, text2: str) -> float:
        text1 = text1.split()
        text2 = text2.split()

        similarity = self.model.wv.n_similarity(text1, text2)

        return round(similarity, 3)