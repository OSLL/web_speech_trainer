import logging
import requests
import time
import traceback

from app.localisation import *
from app.mongo_odm import DBManager, PresentationFilesDBManager, TrainingsDBManager
from app.training import Training
from ..criterion_base import BaseCriterion
from ..criterion_result import CriterionResult
from ..utils import get_proportional_result
from lti.tool_consumer import ToolConsumer


logger = logging.getLogger('root_logger')


class SlidesCheckerCriterion(BaseCriterion):

    PARAMETERS = dict(
        lti_url=str.__name__,
        send_url=str.__name__,
        result_url=str.__name__,
        check_alive_url=str.__name__,
        max_tries=int.__name__,
        pause=int.__name__,
        consumer_key=str.__name__,
        consumer_secret=str.__name__,
        task_params=dict.__name__
    )
    """
    file_type=pres
    pack=<sl-ch_pack_name>
    """

    def __init__(self, parameters, dependent_criteria, name=''):
        super().__init__(
            name=name,
            parameters=parameters,
            dependent_criteria=dependent_criteria,
        )

    @property
    def description(self):
        # TODO: включить критерии?
        return (t('Критерий: {0},\n').format(self.name) +
                t('описание: проверяет соответствие презентации критериям.\n'))

    def apply(self, audio, presentation, training_id, criteria_results):
        training = TrainingsDBManager().get_training(training_id)
        if not training:
            return CriterionResult(0, t('Тренировка отсутствует в БД'))

        pres_file = PresentationFilesDBManager().get_presentation_file(
            training.presentation_file_id)
        if not pres_file:
            return CriterionResult(0, t('Файл презентации отсутствует в БД'))

        if not pres_file.presentation_info.nonconverted_file_id or pres_file.presentation_info.filetype == 'pdf':
            return CriterionResult(0, t('Презентация не имеет поддерживаемого формата (odp, ppt, pptx)'))

        if not self.check_alive(training.username):
            return CriterionResult(0, t('Система проверки недоступна'))
        
        file = DBManager().get_file(pres_file.presentation_info.nonconverted_file_id)

        check_id = self.send_file(file)

        flag, result = self.try_get_result(check_id)
        if not flag:
            return CriterionResult(result=0, verdict=f"Проблемы с проверкой (на стороне инстурмента): {result}")
        else:
            return CriterionResult(result=result['score'], verdict=f"С результатом проверки можно ознакомиться по ссылке: {self.parameters['result_url']}{result['_id']}")

    def check_alive(self, username):
        try:
            alive = requests.get(self.parameters['check_alive_url']) 
            logger.debug('check_alive_url ' + str(alive))
            if alive.status_code != 200:
                return False
            session = requests.Session()
            task_params = self.parameters.get('task_params', {})
            
            custom_params = {'custom_' + key: task_params[key] for key in task_params}
            consumer = self._gen_lti_params(username, custom_params=custom_params)
            launch_params = consumer.generate_launch_data()
            response = session.post(self.parameters['lti_url'], data=launch_params, verify=False)
            if response.status_code == 200:
                self.cookies = session.cookies.get_dict()
                return True
            else:
                logger.warning('check_alive_url ' + str(response.content))
                self.cookies = None
                return False
        except:
            logger.error(traceback.format_exc())
            self.cookies = None
            return False

    def send_file(self, file):
        res = requests.post(self.parameters['send_url'], files={'file': file}, cookies=self.cookies, verify=False)
        return res.json().get('task_id')

    def try_get_result(self, task_id):
        result = None
        time.sleep(self.parameters['pause'])
        for i in range(self.parameters['max_tries']):
            try:
                res = requests.get(f"{self.parameters['send_url']}/{task_id}", cookies=self.cookies, verify=False)
            except Exception as exc:
                logger.error(traceback.format_exc())
                logging.warning(f'Error while checking result: {exc}')
                return False, f"Ошибка во время соединения с инструментом ({exc})"
            res = res.json()
            logger.warning(f'try_get_result: {res}')
            if res['task_status'] != 'SUCCESS':
                time.sleep(self.parameters['pause'])
            else:
                result = res['task_result']
                if isinstance(result, dict):
                    return True, result
                else:
                    return False, f"Проблемы во время проверки ({result})"
        return False, "Max retries to get result"

    def _gen_lti_params(self, username, custom_params={}):
        params = {
                'lti_message_type': 'basic-lti-launch-request',
                'lti_version': 'LTI-1p0',
                'ext_user_username': username,
                'lis_person_name_full': username,
                'roles': 'Student',
                'tool_consumer_instance_guid': "speech-trainer.cub-it.org",
                'lis_outcome_service_url': 'lis_outcome_service_url',
                'lis_result_sourcedid': 'speech-trainer.cub-it.org',
                'resource_link_title': 'speech-trainer-criterion',
                'resource_link_id': 'speech-trainer-criterion',
                **custom_params
        }
        consumer = ToolConsumer(
            consumer_key=self.parameters.get('consumer_key'),
            consumer_secret=self.parameters.get('consumer_secret'),
            launch_url=self.parameters.get('lti_url'),
            params=params
        )
        return consumer
