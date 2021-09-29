from bson import ObjectId
from app.audio import Audio
from app.presentation import Presentation
from .criterion_result import CriterionResult


class BaseCriterion:

    PARAMETERS = dict()

    def __init__(self, parameters: dict, dependent_criteria: list, name=''):
        self.name = name if name else self.__class__.__name__
        self.parameters = parameters
        self.dependent_criteria = dependent_criteria

    @property
    def description(self) -> str:
        raise NotImplementedError()

    def apply(self, audio: Audio, presentation: Presentation, training_id: ObjectId, criteria_results: dict) \
            -> CriterionResult:
        raise NotImplementedError()

    @property
    def dict(self) -> dict:
        return dict(
            name = self.name,
            parameters = self.parameters
        )

    @classmethod
    def structure(cls) -> dict:
        # for simplicity, dependent criteria are removed
        return dict(
            name=cls.__name__,
            parameters=cls.PARAMETERS
        )

    @classmethod
    def from_dict(cls, dictionary):
        dependent_criterions = []   # for simplicity,  dependent criteria are removed
        return cls(dictionary['parameters'], dependent_criterions, name=dictionary.get('name'))
