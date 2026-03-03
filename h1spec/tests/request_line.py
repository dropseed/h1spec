"""Request Line tests (RFC 9112 S3)."""

from __future__ import annotations

from ..client import is_valid_status, parse_status, send_recv
from ..runner import Section, case


def test_simple_get(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Simple GET yields a syntactically valid HTTP response."""
    resp = send_recv(addr, b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
    status = parse_status(resp)
    if is_valid_status(status):
        return True
    return False, f"Expected HTTP status 100-599, got {status}"


def test_post_with_body(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """POST with Content-Length body is accepted (not a parser error)."""
    resp = send_recv(
        addr,
        b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5\r\n\r\nhello",
    )
    status = parse_status(resp)
    if is_valid_status(status) and status != 400:
        return True
    return False, f"Expected valid non-400 status, got {status}"


def test_options_asterisk(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Asterisk-form request-target (OPTIONS *) is parsed."""
    resp = send_recv(addr, b"OPTIONS * HTTP/1.1\r\nHost: localhost\r\n\r\n")
    status = parse_status(resp)
    if is_valid_status(status) and status != 400:
        return True
    return False, f"Expected valid non-400 status, got {status}"


def test_absolute_form(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Absolute-form request-target is parsed."""
    resp = send_recv(
        addr,
        b"GET http://localhost/ HTTP/1.1\r\nHost: localhost\r\n\r\n",
    )
    status = parse_status(resp)
    if is_valid_status(status) and status != 400:
        return True
    return False, f"Expected valid non-400 status, got {status}"


def test_connect_authority_form(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Authority-form request-target (CONNECT) is parsed."""
    resp = send_recv(
        addr, b"CONNECT example.com:443 HTTP/1.1\r\nHost: localhost\r\n\r\n"
    )
    status = parse_status(resp)
    if is_valid_status(status) and status != 400:
        return True
    return False, f"Expected valid non-400 status, got {status}"


def test_invalid_version(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """HTTP/2.0 version string is rejected."""
    resp = send_recv(addr, b"GET / HTTP/2.0\r\nHost: localhost\r\n\r\n")
    status = parse_status(resp)
    if status in (400, 505):
        return True
    return False, f"Expected 400 or 505, got {status}"


def test_malformed_request_line(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Request line with no HTTP version is rejected."""
    resp = send_recv(addr, b"GET /\r\nHost: localhost\r\n\r\n")
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


SECTION = Section(
    "Request Line (RFC 9112 S3)",
    [
        case("Simple GET accepted", test_simple_get),
        case("POST with Content-Length body", test_post_with_body),
        case("OPTIONS * request-target accepted", test_options_asterisk),
        case("Absolute-form request-target accepted", test_absolute_form),
        case("CONNECT authority-form accepted", test_connect_authority_form),
        case("Invalid HTTP version rejected", test_invalid_version),
        case("Malformed request line rejected", test_malformed_request_line),
    ],
)
