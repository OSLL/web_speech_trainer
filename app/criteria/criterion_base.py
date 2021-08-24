from bson import ObjectId
from app.audio import Audio
from app.presentation import Presentation
from .criterion_result import CriterionResult


class Criterion:

    def __init__(self, name: str, parameters: dict, dependent_criteria: list):
        self.name = name
        self.parameters = parameters
        self.dependent_criteria = dependent_criteria

    @property
    def description(self) -> str:
        return ''

    def apply(self, audio: Audio, presentation: Presentation, training_id: ObjectId, criteria_results: dict) \
            -> CriterionResult:
        pass
