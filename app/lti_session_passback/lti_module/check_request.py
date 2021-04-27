from lti.tool_provider import ToolProvider
from .lti_validator import LTIRequestValidator
from ...utils import is_testing_active


def check_request(request_info):
    if not is_testing_active():
        return _check_request(request_info)
    else:
        return _check_request_testing(request_info)


def _check_request(request_info):
    provider = ToolProvider.from_unpacked_request(
        secret=request_info.get('secret', None),
        params=request_info.get('data', {}),
        headers=request_info.get('headers', {}),
        url=request_info.get('url', '')
    )
    return provider.is_valid_request(LTIRequestValidator())


def _check_request_testing(request_info):
    return True
