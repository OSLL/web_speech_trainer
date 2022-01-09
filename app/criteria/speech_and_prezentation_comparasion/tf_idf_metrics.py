class Metric:

    def __init__(self, corpus_tokens):
        self.document_frequency = dict()
        if not corpus_tokens is None:
            for corpus_tokens in [set(tokens) for tokens in corpus_tokens]:
                self.calculate_document_frequency(corpus_tokens)

    @staticmethod
    def calculate_term_frequency(text_tokens):
        words_and_count = dict()
        for word in text_tokens:
            if word not in words_and_count:
                words_and_count[word] = text_tokens.count(word)

        return words_and_count

    # document frequency dictionary updates from one text
    def calculate_document_frequency(self, text_tokens):
        if len(text_tokens) == 0:
            return

        for token in text_tokens:
            if token in self.document_frequency:
                self.document_frequency[token] += 1
            else:
                self.document_frequency[token] = 1

    def get_words_with_metrics(self, text_tokens):
        tf_res = self.calculate_term_frequency(text_tokens)

        metric_result = {key: tf_res[key] if key not in self.document_frequency \
            else tf_res[key] / self.document_frequency[key] for key in tf_res.keys()}

        self.calculate_document_frequency(list(tf_res.keys()))

        return metric_result
