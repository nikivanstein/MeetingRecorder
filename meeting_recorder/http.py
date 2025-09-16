"""Minimal HTTP helpers using the standard library."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib import error, request


class HTTPError(RuntimeError):
    """Raised when an HTTP request returns an error status."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


def _perform_request(req: request.Request, timeout: int) -> str:
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except error.HTTPError as exc:  # pragma: no cover - network error handling
        body = exc.read().decode("utf-8")
        raise HTTPError(exc.code, body) from exc


def post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: int = 60) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = request.Request(url, data=body, headers=req_headers, method="POST")
    response_body = _perform_request(req, timeout)
    return json.loads(response_body)


def post_bytes(url: str, data: bytes, headers: Optional[Dict[str, str]] = None, timeout: int = 60) -> Dict[str, Any]:
    req_headers = headers.copy() if headers else {}
    req = request.Request(url, data=data, headers=req_headers, method="POST")
    response_body = _perform_request(req, timeout)
    return json.loads(response_body)


def get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 60) -> Dict[str, Any]:
    req_headers = headers.copy() if headers else {}
    req = request.Request(url, headers=req_headers, method="GET")
    response_body = _perform_request(req, timeout)
    return json.loads(response_body)
