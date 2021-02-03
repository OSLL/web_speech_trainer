from lti.tool_provider import ToolProvider
from .lti_validator import LTIRequestValidator


def check_request(request_info):
    """
    :request_info: dcit - must include ('headers', 'data', 'secret', 'url') 
    """
    provider = ToolProvider.from_unpacked_request(
        secret=request_info.get('secret', None),
        params=request_info.get('data', {}),
        headers=request_info.get('headers', {}),
        url=request_info.get('url', '')
    )
    return provider.is_valid_request(LTIRequestValidator())