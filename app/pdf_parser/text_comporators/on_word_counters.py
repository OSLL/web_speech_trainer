from app.pdf_parser.text_comporators.base import BaseMeta, BaseTextComporator

from app.pdf_parser.counters.word import WordCounter


class TextComporatorOnWordCounter(BaseTextComporator):
    def __init__(self):
        super(TextComporatorOnWordCounter, self).__init__()
        self.__meta = BaseMeta()

    def cosine_compare(self, text1, text2, get_text1_as_sample=True):
        self._counter1 = WordCounter(text=text1).get_counter()
        self._counter2 = WordCounter(text=text2).get_counter()

        for item in self._counter1:
            if item in self._counter2:
                weight = self._counter2[item] / self._counter1[item]
                if weight > 1:
                    weight = 1
            else:
                weight = 0
            self.__meta.add_text1_token_weight(token=item, weight=weight)

        for item in self._counter2:
            if item in self._counter1:
                weight = self._counter1[item] / self._counter2[item]
                if weight > 1:
                    weight = 1
            else:
                weight = 0
            self.__meta.add_text2_token_weigh(token=item, weight=weight)
        print('On Word Compare : Meta : text 1 : ', self.__meta.text1_token_weights)
        print('On Word Compare : Meta : text 2 : ', self.__meta.text2_token_weights)

        return self._compute_cosine_merics(get_text1_as_sample=get_text1_as_sample)

    def _compute_cosine_merics(self, get_text1_as_sample: bool):
        if get_text1_as_sample:
            text1_weights = sum(self.__meta.text1_token_weights.values())
            return text1_weights / len(self.__meta.text1_token_weights)
        else:
            text2_weights = sum(self.__meta.text2_token_weights.values())
            return text2_weights / len(self.__meta.text2_token_weights)

    def get_meta(self):
        return self.__meta
