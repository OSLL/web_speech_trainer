class BaseMeta:
    def __init__(self):
        self.text1_token_weights = {}
        self.text2_token_weights = {}

    def add_text1_token_weight(self, token, weight):
        self.text1_token_weights[token] = weight

    def add_text2_token_weigh(self, token, weight):
        self.text2_token_weights[token] = weight


class BaseTextComporator:
    def __init__(self):
        pass

    def cosine_compare(self, text1, text2, get_text1_as_sample=True):
        pass

    def _compute_cosine_merics(self, get_text1_as_sample: bool):
        pass

