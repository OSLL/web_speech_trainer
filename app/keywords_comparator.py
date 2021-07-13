from keywords_extraction import Corpus

class KeywordsComparator:

    # audio_keywords        - словарь ключевых слов с метриками из распознанного фрагмента речи
    # presentation_keywords - словарь ключевых слов с метриками из текста презентации
    def __init__(self, audio_keywords, presentation_keywords):
        self.audio_keywords = audio_keywords
        self.presentation_keywords = presentation_keywords

        # Выход - оценка совпадения ключевых слов
    def compare(self, audio_keywords, presentation_keywords):
        return

        # Просто процент совпадения ключевых слов
    def simple_compare_dict(self):
        audio_set = set(self.audio_keywords)
        presentation_set = set(self.presentation_keywords)

        intersection = audio_set & presentation_set

        return len(intersection) / (len(presentation_set))

    def compare_dict(self, level_prezentation, level_audio):
        most_freq_prez  = set(Corpus.choose_keywords(self.presentation_keywords, level = level_prezentation).keys())
        most_freq_audio = set(Corpus.choose_keywords(self.audio_keywords,        level = level_audio).keys())

        least_freq_audio = set(self.audio_keywords.keys()) - most_freq_audio

        concurrence = dict({'NOUN': 0, 'VERB': 0, 'ADJ': 0, 'NOT_IMPORTANT': 0})
        difference  = dict({'NOUN': 0, 'VERB': 0, 'ADJ': 0, 'NOT_IMPORTANT': 0})

        for word in most_freq_prez:
            key, value = Corpus.weight(word)

            if word in most_freq_audio:
                concurrence[key] += value
            elif word in least_freq_audio:
                difference[key] += value
            else:
                k, w = self.not_found(word, most_freq_audio, least_freq_audio)
                if k == 'DIFF':
                    key, value = Corpus.weight(w)
                    difference[key] += value
                elif k == 'CONC':
                    key, value = Corpus.weight(w)
                    concurrence[key] += value

        concurrence_sum = sum(concurrence.values())
        difference_sum = sum(difference.values())
        return concurrence_sum / (concurrence_sum + difference_sum)

    @staticmethod
    def not_found(word, most_frec, least_frec):
        stem = Corpus.stemmer(word)

        for token in most_frec:
            if token.find(stem) > -1:
                return ('CONC', token)
        for token in least_frec:
            if token.find(stem) > -1:
                return ('DIFF', token)
        return ('NOT_FOUND', -1)


    def compare_dict_without_stemming(self, level_prezentation, level_audio):
        most_freq_prez  = set(Corpus.choose_keywords(self.presentation_keywords, level = level_prezentation).keys())
        most_freq_audio = set(Corpus.choose_keywords(self.audio_keywords,        level = level_audio).keys())

        least_freq_audio = set(self.audio_keywords.keys()) - most_freq_audio

        concurrence = dict({'NOUN': 0, 'VERB': 0, 'ADJ': 0, 'NOT_IMPORTANT': 0})
        difference  = dict({'NOUN': 0, 'VERB': 0, 'ADJ': 0, 'NOT_IMPORTANT': 0})

        for word in most_freq_prez:
            key, value = Corpus.weight(word)

            if word in most_freq_audio:
                concurrence[key] += value
            else:
                difference[key] += value

        concurrence_sum = sum(concurrence.values())
        difference_sum = sum(difference.values())
        return concurrence_sum / (concurrence_sum + difference_sum)