class Metric:
    @staticmethod
    def calculate_term_frequency(text_tokens, more_important_words: set = []):
        words_and_count = dict()
        for word in text_tokens:
            if word not in words_and_count:
                words_and_count[word] = text_tokens.count(word)
                if word in more_important_words:
                    words_and_count[word] += 2
        return words_and_count

    def get_words_with_metrics(self, text_tokens, more_important_words: set = []):
        tf_res = self.calculate_term_frequency(text_tokens, more_important_words)
        return {key: tf_res[key] for key in tf_res.keys()}
