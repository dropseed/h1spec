"""Header tests (RFC 9112 S5)."""

from __future__ import annotations

from ..client import parse_status, send_recv
from ..runner import Section, case


def test_missing_host(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Missing Host header in HTTP/1.1 request is rejected (RFC 9112 S3.2)."""
    resp = send_recv(addr, b"GET / HTTP/1.1\r\n\r\n")
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def test_duplicate_host(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Multiple Host headers in HTTP/1.1 are rejected."""
    resp = send_recv(
        addr, b"GET / HTTP/1.1\r\nHost: localhost\r\nHost: example.com\r\n\r\n"
    )
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def test_invalid_host_value(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Host field-value with invalid whitespace is rejected."""
    resp = send_recv(
        addr,
        b"GET / HTTP/1.1\r\nHost: bad host\r\n\r\n",
    )
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def test_invalid_header_name(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Header name containing a space is rejected."""
    resp = send_recv(
        addr, b"GET / HTTP/1.1\r\nHost: localhost\r\nBad Header: value\r\n\r\n"
    )
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def test_obsolete_folding(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Obsolete header line folding (RFC 7230) is rejected."""
    resp = send_recv(addr, b"GET / HTTP/1.1\r\nHost: localhost\r\n  continued\r\n\r\n")
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def test_space_before_colon(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Space before the colon in a header is rejected."""
    resp = send_recv(addr, b"GET / HTTP/1.1\r\nHost : localhost\r\n\r\n")
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def test_null_in_header(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Null byte in header value is rejected."""
    resp = send_recv(addr, b"GET / HTTP/1.1\r\nHost: local\x00host\r\n\r\n")
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


SECTION = Section(
    "Headers (RFC 9112 S5)",
    [
        case("Missing Host header rejected", test_missing_host),
        case("Duplicate Host rejected", test_duplicate_host),
        case("Invalid Host value rejected", test_invalid_host_value),
        case("Invalid header name rejected", test_invalid_header_name),
        case("Obsolete line folding rejected", test_obsolete_folding),
        case("Space before colon rejected", test_space_before_colon),
        case("Null byte in header rejected", test_null_in_header),
    ],
)
