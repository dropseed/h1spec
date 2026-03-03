"""Hardening tests (implementation-defined limits)."""

from __future__ import annotations

from ..client import is_valid_status, parse_status, send_recv
from ..runner import Section, case


def _probe_alive(addr: tuple[str, int]) -> bool:
    probe = send_recv(addr, b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
    return is_valid_status(parse_status(probe))


def test_oversized_request_line(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Very long request-line does not destabilize the server."""
    long_path = b"/" + b"a" * 9000
    resp = send_recv(
        addr, b"GET " + long_path + b" HTTP/1.1\r\nHost: localhost\r\n\r\n"
    )
    status = parse_status(resp)
    if status != 0 and not is_valid_status(status):
        return False, f"Malformed response to oversized request-line: {status}"
    if _probe_alive(addr):
        return True
    return False, "Server did not respond to follow-up request after oversized line"


def test_header_flood(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Large header counts are rejected or otherwise handled without destabilizing."""
    headers = b"".join(f"X-H-{i}: value\r\n".encode() for i in range(101))
    resp = send_recv(addr, b"GET / HTTP/1.1\r\nHost: localhost\r\n" + headers + b"\r\n")
    status = parse_status(resp)
    if status != 0 and not is_valid_status(status):
        return False, f"Malformed response to header flood: {status}"
    if _probe_alive(addr):
        return True
    return False, "Server did not respond to follow-up request after header flood"


def test_oversized_header(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Oversized single header is rejected or safely handled."""
    big_value = b"x" * 9000
    resp = send_recv(
        addr,
        b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Big: " + big_value + b"\r\n\r\n",
    )
    status = parse_status(resp)
    if status != 0 and not is_valid_status(status):
        return False, f"Malformed response to oversized header: {status}"
    if _probe_alive(addr):
        return True
    return False, "Server did not respond to follow-up request after oversized header"


SECTION = Section(
    "Hardening (Implementation-defined limits)",
    [
        case(
            "Oversized request line",
            test_oversized_request_line,
            hardening=True,
        ),
        case("Header flood", test_header_flood, hardening=True),
        case(
            "Oversized header",
            test_oversized_header,
            hardening=True,
        ),
    ],
)
