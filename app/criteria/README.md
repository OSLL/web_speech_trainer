# Критерии

## Структура класса критерия
Все классы критериев
- наследуются от класса `Critetion` модуля `criterion_base`
- реализуют
  - метод `__init__`, принимающий словарь параметров критерия и список зависимых критериев, **обязательно** вызывающий соответствующий метод базового класса
  - свойство `description` - текстовое описание критерия
  - метод `apply` - основной метод критерия, возвращающий объект класса `CriterionResult` модуля `criterion_result`
  - поле класса `PARAMETERS` - словарь вида `{имя_параметра: тип_параметра}`
    - `тип_параметра` - строка, полученная, например, с помощью `list.__name__`
    - только стандартные форматы: _str/int/float/list/dict_

Минимально жизнеспособный критерий: 
```
class EmptyCriterion:

    PARAMETERS = dict()

    def __init__(self, parameters: dict, dependent_criteria: list):
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self) -> str:
        return ""

    def apply(self, audio: Audio, presentation: Presentation, training_id: ObjectId, criteria_results: dict) -> CriterionResult:
        return CriterionResult(1)
```

## Правила реализации и работы с модулями
- Все файлы, необходимые для критерия, размещаются в директории с именем, соответствующем названию критерия в стиле `lower_case_with_underscores`.
- Класс критерия размещается в файле `criterion.py`
- Для возможности импорта критерия в других модулях системы, необходимо разместить импорт класса критерия в `critetions.py`
    - Внешние модули должны знать только классы критериев - никакие другие функции/классы/переменные не импортируются и не выносятся
```
from .empty_criterion.criterion import EmptyCriterion
```
- Наличие readme, описывающего параметры критерия и его цель, в директории приветствуются.
