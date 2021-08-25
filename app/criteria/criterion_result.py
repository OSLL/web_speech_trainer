import json
from typing import Optional
from app.localisation import *


class CriterionResult:

    def __init__(self, result: float, verdict: Optional[str] = None):
        self.result = result
        self.verdict = verdict

    def __str__(self):
        if self.verdict is not None:
            return t('Вердикт: {}, результат = {:.3f} очков').format(self.verdict, self.result)
        else:
            return t('Результат = {:.3f} очков').format(self.result)

    def to_json(self) -> dict:
        return {
            'verdict': None if self.verdict is None else repr(self.verdict),
            'result': self.result,
        }

    @staticmethod
    def from_json(json_file):
        json_obj = json.loads(json_file)
        json_verdict = json_obj['verdict']
        json_result = json_obj['result']
        return CriterionResult(json_result, json_verdict)
