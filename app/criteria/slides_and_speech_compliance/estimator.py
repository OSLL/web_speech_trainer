class Estimator:
    def __init__(self, parser, weights=None, skipped_coef=0.75):
        self.parser = parser
        # by title
        self.higher_weight = {'задач', 'работ', 'цел', 'метод', 'заключен', 'обзор', 'разработк', 'приложен', 'функц', 'метод', 'актуальн', 'объект', 'модел', 'разработа', 'модул'}
        self.lower_weight = {'пример', 'модел', 'алгоритм', 'апробац', 'спасибо', 'внимание', 'команд', 'рисунок', 'график', 'сравнен', 'эксперимент', 'архитектур', 'результат','реализац', 'диаграмм', 'интерфейс'}
        # for lower weight slides, for normal and for higher weight slides
        self.weights = [0.3, 1, 1.7] if weights is None else weights
        # for first slide identification
        self.title_slide_words = {'студент', 'выполнил', 'руководитель', 'групп', 'тема', 'лэти', 'автор'}
        self.skipped_coef = skipped_coef

    def get_weight_by_title(self, title):
        title = self.parser.get_special_stems(self.parser.parse(title), [])

        if title is None or len(title) == 0:
            return 1

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

    def get_slides_estimate(self, results_per_slide, skipped_slides_count):
        if len(results_per_slide) == 0:
            return 0
        max_result = sum([weight for (value, weight) in results_per_slide])
        result = sum([value * weight for (value, weight) in results_per_slide])
        mark = result / max_result
        skipped_weight = skipped_slides_count / (len(results_per_slide) + skipped_slides_count) * self.skipped_coef
        return mark * (1 - skipped_weight)

    @staticmethod
    def coordinate_soft_and_hard_estimates(soft, hard):
        return hard + (1 - hard) * soft if soft > 0.0 else hard

    @staticmethod
    def estimate_by_intersection(main_text, general_text):
        if not isinstance(main_text, set):
            main_text = set(main_text)

        if not isinstance(general_text, set):
            general_text = set(general_text)

        coincidence = len(main_text.intersection(general_text))

        return 0 if len(main_text) == 0 else coincidence / len(main_text)
