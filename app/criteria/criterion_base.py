from bson import ObjectId
from app.audio import Audio
from app.presentation import Presentation
from .criterion_result import CriterionResult


class Criterion:

    def __init__(self, parameters: dict, dependent_criteria: list):
        self.name = self.__class__.__name__
        self.parameters = parameters
        self.dependent_criteria = dependent_criteria

    @property
    def description(self) -> str:
        raise NotImplementedError()

    def apply(self, audio: Audio, presentation: Presentation, training_id: ObjectId, criteria_results: dict) \
            -> CriterionResult:
        raise NotImplementedError()
