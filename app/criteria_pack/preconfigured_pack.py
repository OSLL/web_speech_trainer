from app.mongo_odm import CriterionPackDBManager

pack_configuration = {
    'DuplicateAudioPack':
        ['DEFAULT_SPEECH_IS_NOT_IN_DATABASE_CRITERION'],
    'FifteenMinutesTrainingPack':
        ['FifteenMinutesSpeechDurationCriterion',
         'DEFAULT_SPEECH_PACE_CRITERION',
         'DEFAULT_FILLERS_RATIO_CRITERION'],
    'FillersRatioPack':
        ['DEFAULT_FILLERS_RATIO_CRITERION'],
    'PaceAndDurationPack':
        ['SimpleDurationCriterion',
         'SimpleSpeechPaceCriterion'],
    'PredefenceEightToTenMinutesPack':
        ['PredefenceStrictSpeechDurationCriterion',
         'DEFAULT_SPEECH_PACE_CRITERION',
         'DEFAULT_FILLERS_NUMBER_CRITERION'],
    'PrimitivePack':
        ['SimpleDurationCriterion',
         'SimpleNumberWordOnSlideCriterion',
         'SimpleNumberSlidesCriterion'],
    'SimplePack': ['SimpleDurationCriterion'],
    'TenMinutesTrainingPack':
        ['TenMinutesSpeechDurationCriterion',
         'DEFAULT_SPEECH_PACE_CRITERION',
         'DEFAULT_FILLERS_RATIO_CRITERION'],
    'TwentyMinutesTrainingPack':
        ['FifteenMinutesSpeechDurationCriterion',
         'DEFAULT_SPEECH_PACE_CRITERION',
         'DEFAULT_FILLERS_RATIO_CRITERION']}


def add_preconf_packs():
    for pack_name, criteria in pack_configuration.items():
        CriterionPackDBManager().add_pack_from_names(pack_name, criteria)
