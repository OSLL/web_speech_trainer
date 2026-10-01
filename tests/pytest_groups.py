"""
Pytest plugin: groups of test cases.

All groups are listed in GROUPS (unit and selenium tests together).
Tests are assigned to groups with marker `@pytest.mark.group('name', ...)` (module, class or function level,
a test belongs to all groups from all its markers). Every test must be in at least one group from GROUPS,
otherwise the run fails at collection.
Env var TEST_GROUPS - list of groups to run (separated by commas and/or spaces), e.g. TEST_GROUPS="api,speech_pace".
If TEST_GROUPS is empty or not set, all tests are run. Unknown group in TEST_GROUPS is an error.

Plugin is connected in tests/conftest.py (unit tests) and tests/selenium/conftest.py (selenium tests).
"""
import os
import re

import pytest

ENV_VAR = 'TEST_GROUPS'
MARKER = 'group'

GROUPS = {
    # unit tests
    'app': 'test_app.py - страница /init/, критерий FillersRatioCriterion',
    'audio_conversion': 'test_audio_conversion.py - шумоподавление аудио (Denoiser)',
    'feedback_evaluator': 'test_feedback_evaluator.py',
    'presentations': 'test_presentations.py - разбиение распознанной презентации на слайды',
    'whisper': 'test_whisper.py - распознавание речи (нужен запущенный whisper)',
    'api': 'все тесты api/',
    'api_audio': 'api/test_audio.py',
    'api_files': 'api/test_files.py',
    'api_task_attempts': 'api/test_task_attempts.py',
    'criteria': 'все тесты criteria/',
    'criteria_common': 'общие тесты критериев (TestCriterionContract: параметры, описания, get_proportional_result)',
    'comparison_speech_slides': 'ComparisonSpeechSlidesCriterion',
    'comparison_whole_speech': 'ComparisonWholeSpeechCriterion',
    'fillers_number': 'FillersNumberCriterion',
    'fillers_ratio': 'FillersRatioCriterion',
    'len_text_on_slide': 'LenTextOnSlideCriterion',
    'number_slides': 'NumberSlidesCriterion',
    'number_word_on_slide': 'NumberWordOnSlideCriterion',
    'slides_checker': 'SlidesCheckerCriterion',
    'speech_duration': 'SpeechDurationCriterion',
    'speech_is_not_in_database': 'SpeechIsNotInDatabaseCriterion',
    'speech_pace': 'SpeechPaceCriterion',
    'strict_speech_duration': 'StrictSpeechDurationCriterion',
    # selenium tests
    'selenium': 'все selenium тесты',
    'simple_training': 'selenium: простая тренировка (test_simple_training.py)',
}


def groups_help():
    return 'available groups:\n' + '\n'.join(f'  {name} - {description}' for name, description in GROUPS.items())


def requested_groups():
    return [name for name in re.split(r'[,\s]+', os.environ.get(ENV_VAR, '')) if name]


def item_groups(item):
    return {name for marker in item.iter_markers(MARKER) for name in marker.args}


def pytest_configure(config):
    config.addinivalue_line('markers', f'{MARKER}(*names): test groups, run only some of them with env var {ENV_VAR}')

    unknown = [name for name in requested_groups() if name not in GROUPS]
    if unknown:
        raise pytest.UsageError(f'{ENV_VAR}: unknown groups {", ".join(unknown)}\n{groups_help()}')


def pytest_report_header(config):
    groups = requested_groups()
    return f'test groups ({ENV_VAR}): {", ".join(groups) if groups else "all"}'


def pytest_collection_modifyitems(session, config, items):
    errors = []
    for item in items:
        groups = item_groups(item)
        if not groups:
            errors.append(f'{item.nodeid}: no groups, add marker @pytest.mark.{MARKER}(...)')
        elif groups - GROUPS.keys():
            errors.append(f'{item.nodeid}: unknown groups {", ".join(sorted(groups - GROUPS.keys()))}')
    if errors:
        raise pytest.UsageError(
            f'tests groups errors (groups are listed in GROUPS in {__file__}):\n' + '\n'.join(errors)
        )

    groups = set(requested_groups())
    if not groups:
        return

    selected, deselected = [], []
    for item in items:
        (selected if item_groups(item) & groups else deselected).append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


def pytest_sessionfinish(session, exitstatus):
    # unit and selenium tests are separate runs with the same TEST_GROUPS,
    # no tests of requested groups in this run (e.g. only unit test groups are requested in selenium run) is not a failure
    if requested_groups() and exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK
