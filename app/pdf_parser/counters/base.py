class BaseCounter:
    def __init__(self, text):
        self._items = {}
        self._text = text

    def add(self, item):
        if item not in self._items:
            self._items[item] = 1
        else:
            self._items[item] += 1

    def get_counter(self):
        return self._items

    def _compute_freq(self):
        pass