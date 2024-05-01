from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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
