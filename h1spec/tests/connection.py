"""Connection tests (RFC 9112 S9)."""

from __future__ import annotations

from ..client import (
    close_socket,
    connect,
    is_valid_status,
    parse_status,
    recv_one_response,
)
from ..runner import Section, case


def test_keepalive_default(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Two requests on one socket both get responses (HTTP/1.1 keep-alive)."""
    s = connect(addr)
    s.settimeout(5)

    s.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
    resp1 = recv_one_response(s)
    status1 = parse_status(resp1)
    if status1 == 0:
        close_socket(s)
        return False, "No response to first request"

    s.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
    resp2 = recv_one_response(s)
    status2 = parse_status(resp2)
    close_socket(s)

    if is_valid_status(status1) and is_valid_status(status2):
        return True
    return False, f"First: {status1}, Second: {status2}"


def _assert_server_closes(
    addr: tuple[str, int], request: bytes
) -> bool | tuple[bool, str]:
    """Send a request and verify the server closes the connection after responding."""
    s = connect(addr)
    s.settimeout(5)
    try:
        s.sendall(request)
        chunks: list[bytes] = []
        try:
            while chunk := s.recv(4096):
                chunks.append(chunk)
        except TimeoutError:
            return False, "Server did not close connection"
        resp = b"".join(chunks)
        status = parse_status(resp)
        if status > 0:
            return True
        return False, "No response"
    finally:
        close_socket(s)


def test_connection_close(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Server closes connection after Connection: close request."""
    return _assert_server_closes(
        addr, b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
    )


def test_http10_closes(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """HTTP/1.0 connection closes by default after one response."""
    return _assert_server_closes(addr, b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n")


SECTION = Section(
    "Connection (RFC 9112 S9)",
    [
        case("Keep-alive default (HTTP/1.1)", test_keepalive_default),
        case("Connection: close honored", test_connection_close),
        case("HTTP/1.0 closes by default", test_http10_closes),
    ],
)
