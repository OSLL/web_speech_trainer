from app.mongo_odm import CriterionPackDBManager

pack_configuration = {
    'DuplicateAudioPack':
        [['DEFAULT_SPEECH_IS_NOT_IN_DATABASE_CRITERION', 1]],
    'FifteenMinutesTrainingPack':
        [['FifteenMinutesSpeechDurationCriterion', 0.33],
         ['DEFAULT_SPEECH_PACE_CRITERION', 0.33],
         ['DEFAULT_FILLERS_RATIO_CRITERION', 0.33]],
    'FillersRatioPack':
        [['DEFAULT_FILLERS_RATIO_CRITERION', 1]],
    'PaceAndDurationPack':
        [['SimpleDurationCriterion', 0.5],
         ['SimpleSpeechPaceCriterion', 0.5]],
    'PredefenceEightToTenMinutesPack':
        [['PredefenceStrictSpeechDurationCriterion', 0.6],
         ['DEFAULT_SPEECH_PACE_CRITERION', 0.2],
         ['DEFAULT_FILLERS_NUMBER_CRITERION', 0.2]],
    'PrimitivePack':
        [['SimpleDurationCriterion', 0.33],
         ['SimpleNumberWordOnSlideCriterion', 0.33],
         ['SimpleNumberSlidesCriterion', 0.33]],
    'SimplePack': [['SimpleDurationCriterion', 0.55],
                   ['SimpleNumberSlidesCriterion', 0.45]],
    'TenMinutesTrainingPack':
        [['TenMinutesSpeechDurationCriterion', 0.33],
         ['DEFAULT_SPEECH_PACE_CRITERION', 0.33],
         ['DEFAULT_FILLERS_RATIO_CRITERION', 0.33]],
    'TwentyMinutesTrainingPack':
        [['TwentyMinutesSpeechDurationCriterion', 0.33],
         ['DEFAULT_SPEECH_PACE_CRITERION', 0.33],
         ['DEFAULT_FILLERS_RATIO_CRITERION', 0.33]],
    'SlidesCheckerPack':
        [['SimpleNumberSlidesCriterion', 0.05],
         ['SlidesCheckerCriterion', 0.95]],
    'ComparisonPack':
    [['ComparisonSpeechSlidesCriterion', 0.5],
     ['ComparisonWholeSpeechCriterion', 0.5]]
}


def add_preconf_packs():
    for pack_name, criterion_info in pack_configuration.items():
        CriterionPackDBManager().add_pack_from_names(
            pack_name, (critetion[0] for critetion in criterion_info), weights=dict(criterion_info))
