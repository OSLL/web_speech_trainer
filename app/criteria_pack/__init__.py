from app.criteria_pack.criterion_pack_base import BaseCriterionPack
from app.mongo_odm import CriterionPackDBManager


class CriteriaPackFactory:
    def get_criteria_pack(self, criteria_pack_name):
        pack = CriterionPackDBManager().get_criterion_pack_by_name(criteria_pack_name)
        if not pack:
            pack = CriterionPackDBManager().get_criterion_pack_by_name("SimplePack")
        return BaseCriterionPack.from_dict(pack.to_dict())
