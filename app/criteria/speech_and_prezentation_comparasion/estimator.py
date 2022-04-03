class Estimator:
    def __init__(self, parser):
        self.parser = parser
        # by title
        self.higher_weight = {'задача', 'приложение', 'цель', 'метод', 'актуальность', 'обзор', 'решение', 'результат'}
        self.lower_weight = {'пример', 'модель', 'данные', 'технология', 'спасибо', 'внимание', 'команда'}
        # for lower weight slides, for normal and for higher weight slides
        self.weights = [0.7, 1, 1.3]

        # for first slide identification
        self.title_slide_words = {'студент', 'выполнил', 'руководитель', 'групп', 'тема', 'лэти', 'автор'}

    def get_weight_by_title(self, title):
        if title is None or len(title) == 0:
            return 1

        title = self.parser.parse(title)
        result = 0.0
        for word in title:
            if word in self.higher_weight:
                result += self.weights[2]
            elif word in self.lower_weight:
                result += self.weights[0]
            else:
                result += self.weights[1]

        return result / float(len(title))

    def is_title_slide(self, text: str):
        count = 0
        for word in self.title_slide_words:
            if text.find(word) > 0:
                count += 1
        return count > 2

    @staticmethod
    def get_slides_estimate(title_weights, results_per_slide):
        return 0 if len(title_weights) == 0 \
            else sum([a * b for a, b in zip(title_weights, results_per_slide)]) / sum(title_weights)

    @staticmethod
    def coordinate_soft_and_hard_estimates(soft, hard):
        return hard + (1 - hard) * soft if soft > 0.0 else hard
