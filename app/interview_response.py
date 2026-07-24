from dataclasses import dataclass, field
from typing import Any

from flask import jsonify, redirect


@dataclass(slots=True)
class ApiResponse:
    payload: dict[str, Any] = field(default_factory=dict)
    status_code: int = 200

    def to_flask(self):
        return jsonify(self.payload), self.status_code

    @classmethod
    def ok(cls, **payload):
        return cls(payload=payload, status_code=200)

    @classmethod
    def created(cls, **payload):
        return cls(payload=payload, status_code=201)

    @classmethod
    def error(cls, error: str, status_code: int = 400, **payload):
        return cls(payload={'error': error, **payload}, status_code=status_code)

    @classmethod
    def success(cls, redirect_url: str | None = None, status_code: int = 200, **payload):
        data = {'status': 'success', **payload}
        if redirect_url is not None:
            data['redirect_url'] = redirect_url
        return cls(payload=data, status_code=status_code)

    @classmethod
    def failure(
        cls,
        error: str,
        status_code: int = 400,
        redirect_url: str | None = None,
        **payload,
    ):
        data = {'status': 'failure', 'error': error, **payload}
        if redirect_url is not None:
            data['redirect_url'] = redirect_url
        return cls(payload=data, status_code=status_code)

    @classmethod
    def processing(cls, status_text: str, task_status: str | None = None, **payload):
        data = {'status': 'processing', 'status_text': status_text, **payload}
        if task_status is not None:
            data['task_status'] = task_status
        return cls(payload=data, status_code=200)


@dataclass(slots=True)
class PageResponse:
    body: Any
    status_code: int | None = None

    def to_flask(self):
        if self.status_code is None:
            return self.body
        return self.body, self.status_code

    @classmethod
    def text(cls, body: str, status_code: int = 200):
        return cls(body=body, status_code=status_code)

    @classmethod
    def html(cls, body: Any, status_code: int = 200):
        return cls(body=body, status_code=status_code)

    @classmethod
    def empty(cls, status_code: int = 200):
        return cls(body='', status_code=status_code)

    @classmethod
    def redirect(cls, location: str):
        return cls(body=redirect(location), status_code=None)