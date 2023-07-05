from app.criteria import CRITERIONS
import logging
from app.localisation import *
from app.mongo_odm import CriterionDBManager, TrainingsDBManager

logger = logging.getLogger('root_logger')


class BaseCriterionPack:

    def __init__(self, criteria, name=''):
        self.name = name if name else self.__class__.__name__
        self.criteria = criteria
        self.criteria_results = {}

    def add_criterion_result(self, name, criterion_result):
        self.criteria_results[name] = criterion_result

    def apply(self, audio, presentation, training_id):
        logger.info(
            'Called {}.apply for a training with training_id = {}'.format(self.name, training_id))
        for criterion in self.criteria:
            try:
                criterion_result = criterion.apply(
                    audio, presentation, training_id, self.criteria_results)
                self.add_criterion_result(criterion.name, criterion_result)
                TrainingsDBManager().add_criterion_result(
                    training_id, criterion.name, criterion_result)
                logger.info('Attached {} {} to a training with training_id = {}'
                            .format(criterion.name, criterion_result, training_id))
            except Exception as e:
                logger.warning('Exception while applying {} for a training with training_id = {}.\n{}: {}'
                               .format(criterion.name, training_id, e.__class__, e))
        return self.criteria_results

    def get_criterion_by_name(self, criterion_name):
        for criterion in self.criteria:
            if criterion.name == criterion_name:
                return criterion
        return None

    # TODO move to feedback evaluator
    def get_criteria_pack_weights_description(self, weights: dict) -> any:
        description = {"Критерии":[]}
        for criterion in self.criteria:
            criteria_tmp = criterion.description
            if weights and criterion.name in weights:
                criteria_tmp["Вес"] = "{:.3f}".format(weights[criterion.name])
                description["Критерии"].append(criteria_tmp)

            else:
                criteria_tmp["Вес"]  = "1 / {}".format(len(self.criteria))
                description["Критерии"].append(criteria_tmp)

        return description

    @property
    def dict(self) -> dict:
        return dict(
            name=self.name,
            criteria=[criterion.name for criterion in self.criteria]
        )

    @classmethod
    def from_dict(cls, dictionary):
        # 'criterions' in dictionary is list of criterion's names (=> to class instance)
        criteria = []
        for name in dictionary['criterions']:
            # get criterion info from db
            db_criterion = CriterionDBManager().get_criterion_by_name(name)
            if not db_criterion:
                continue
            # create instance of criterion
            criterion_class = CRITERIONS.get(db_criterion.base_criterion)
            if criterion_class:
                criteria.append(criterion_class.from_dict(db_criterion.to_dict()))

        return cls(criteria, name=dictionary.get('name'))
