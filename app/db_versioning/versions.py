class Version:
    VERSION_NAME = '0.1'
    CHANGES = ""

    @classmethod
    def update_database(cls, collections, prev_version):
        """
        <collections> must contains (objects from pymongo)
        - users
        - presentations
        - checks
        """
        raise NotImplementedError()

    @classmethod
    def to_dict(cls):
        return dict(
            version=cls.VERSION_NAME,
            changes=cls.CHANGES
        )

    @staticmethod
    def get_version(version_name):
        for version in VERSIONS:
            if version.version == version_name:
                return version
        return None


class Version10(Version):
    VERSION_NAME = '1.0'
    CHANGES = "Начальная версия БД"

    @classmethod
    def update_database(cls, db, prev_version):
        pass


class Version20(Version):
    VERSION_NAME = '2.0'
    CHANGES = "Перевод criteria_pack_id из IntField в CharField с использованием сконфигурированных наборов"
    SUPPORTED_PREV_VERSIONS = (Version10.VERSION_NAME, )

    @classmethod
    def update_database(cls, db, prev_version):
        CRITERIA_PACK_CLASS_BY_ID = {
            1: 'SimplePack',
            2: 'PaceAndDurationPack',
            3: 'FillersRatioPack',
            4: 'DuplicateAudioPack',
            5: 'TenMinutesTrainingPack',
            6: 'FifteenMinutesTrainingPack',
            7: 'TwentyMinutesTrainingPack',
            8: 'PredefenceEightToTenMinutesPack',
            9: 'PrimitivePack',
            10: 'ComparisonPack'
        }

        if prev_version in cls.SUPPORTED_PREV_VERSIONS:
            for pack_id, pack_name in CRITERIA_PACK_CLASS_BY_ID.items():
                find_query = {'criteria_pack_id': pack_id}
                update_query = {'$set': {'criteria_pack_id': pack_name}}
                db['trainings'].update_many(find_query, update_query)
                db['tasks'].update_many(find_query, update_query)
        else:
            raise Exception(
                f'Неподдерживаемый переход с версии {prev_version}')


class Version21(Version20):
    VERSION_NAME = '2.1'
    CHANGES = "Repeat version 2.0 with updated PyMongo methods"
    SUPPORTED_PREV_VERSIONS = (Version10.VERSION_NAME, Version20.VERSION_NAME)


VERSIONS = {
    '1.0': Version10,
    '2.0': Version20,
    '2.1': Version21
}
LAST_VERSION = '2.1'


for _, ver in VERSIONS.items():
    print(ver.to_dict())
