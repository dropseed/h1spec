"""Response Semantics tests (RFC 9110)."""

from __future__ import annotations

from ..client import (
    get_body,
    has_close_token,
    is_chunked,
    is_valid_status,
    parse_content_length,
    parse_headers,
    parse_status,
    send_recv,
)
from ..runner import Section, case


def test_head_no_body(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """HEAD response contains zero body bytes."""
    resp = send_recv(addr, b"HEAD / HTTP/1.1\r\nHost: localhost\r\n\r\n")
    status = parse_status(resp)
    if status == 0:
        return False, "No response"
    body = get_body(resp)
    if len(body) == 0:
        return True
    return False, f"Expected empty body, got {len(body)} bytes"


def test_error_response_delimiting(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Error responses are self-delimiting (Content-Length, chunked, or close)."""
    resp = send_recv(addr, b"get / HTTP/1.1\r\nHost: localhost\r\n\r\n")
    status = parse_status(resp)
    if not is_valid_status(status):
        return False, "No valid error response"

    headers = parse_headers(resp)
    if parse_content_length(headers) is not None:
        return True
    if is_chunked(headers):
        return True
    if has_close_token(headers.get(b"connection", b"")):
        return True
    return (
        False,
        "Expected Content-Length, chunked transfer-encoding, or Connection: close",
    )


SECTION = Section(
    "Response Semantics (RFC 9110)",
    [
        case("HEAD response has no body", test_head_no_body),
        case("Error response is self-delimiting", test_error_response_delimiting),
    ],
)
