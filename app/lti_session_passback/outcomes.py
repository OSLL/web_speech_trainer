"""LTI outcome transport with bounded network operations."""

import requests
from lti import OutcomeRequest, OutcomeResponse
from oauthlib.oauth1 import SIGNATURE_TYPE_AUTH_HEADER
from requests_oauthlib import OAuth1


class BoundedOutcomeRequest(OutcomeRequest):
    def post_outcome_request(self, **kwargs):
        if not self.has_required_attributes():
            raise ValueError("Missing LTI outcome parameters")
        auth = OAuth1(
            self.consumer_key,
            self.consumer_secret,
            signature_type=SIGNATURE_TYPE_AUTH_HEADER,
            force_include_body=True,
            **kwargs,
        )
        response = requests.post(
            self.lis_outcome_service_url,
            auth=auth,
            data=self.generate_request_xml(),
            headers={"Content-type": "application/xml"},
            timeout=(10, 60),
        )
        response.raise_for_status()
        return OutcomeResponse.from_post_response(response, response.content)


def replace_score(params, secret, score):
    request = BoundedOutcomeRequest(
        opts={
            "consumer_key": params["oauth_consumer_key"],
            "consumer_secret": secret,
            "lis_outcome_service_url": params["lis_outcome_service_url"],
            "lis_result_sourcedid": params["lis_result_sourcedid"],
        }
    )
    response = request.post_replace_result(score)
    if response.code_major != "success" or response.severity != "status":
        raise RuntimeError(
            f"LMS rejected outcome: {response.code_major}: {response.description}"
        )
