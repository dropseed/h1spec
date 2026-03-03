"""Body tests (RFC 9112 S6-7)."""

from __future__ import annotations

from ..client import (
    close_socket,
    connect,
    extract_status_codes,
    is_valid_status,
    parse_status,
    read_all_statuses_on_close,
    read_until_close,
    recv_one_response,
    response_signals_close,
    send_recv,
)
from ..runner import Section, case


def test_chunked_encoding(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Valid chunked POST is accepted (not a parser error)."""
    data = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b"5\r\nhello\r\n"
        b"0\r\n\r\n"
    )
    resp = send_recv(addr, data)
    status = parse_status(resp)
    if status != 400:
        return True
    return False, f"Expected non-400, got {status}"


def test_chunked_http10(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Chunked transfer encoding with HTTP/1.0 is rejected."""
    data = (
        b"POST / HTTP/1.0\r\n"
        b"Host: localhost\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b"5\r\nhello\r\n"
        b"0\r\n\r\n"
    )
    resp = send_recv(addr, data)
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def test_chunked_plus_content_length(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Both Transfer-Encoding: chunked and Content-Length is rejected."""
    data = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"Content-Length: 5\r\n"
        b"\r\n"
        b"5\r\nhello\r\n"
        b"0\r\n\r\n"
    )
    resp = send_recv(addr, data)
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def test_chunked_plus_content_length_closes(
    addr: tuple[str, int],
) -> bool | tuple[bool, str]:
    """TE+CL response closes the connection before a second request can be served."""
    s = connect(addr)
    s.settimeout(5)
    try:
        req = (
            b"POST / HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Content-Length: 5\r\n"
            b"\r\n"
            b"5\r\nhello\r\n"
            b"0\r\n\r\n"
        )
        s.sendall(req)
        first = recv_one_response(s, request_method=b"POST")
        first_status = parse_status(first)
        if not is_valid_status(first_status):
            return False, f"Expected valid first response, got {first_status}"

        if response_signals_close(first):
            return True

        try:
            s.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        except OSError:
            return True
        second = recv_one_response(s)
        second_status = parse_status(second)
        if second_status == 0:
            return True
        return (
            False,
            f"Expected connection close after TE+CL, got second status {second_status}",
        )
    finally:
        close_socket(s)


def test_unknown_transfer_encoding(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Unknown transfer-coding is rejected."""
    req = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Transfer-Encoding: nonsense\r\n"
        b"\r\n"
        b"hello"
    )
    resp = send_recv(addr, req)
    status = parse_status(resp)
    if status in (400, 501):
        return True
    return False, f"Expected 400 or 501, got {status}"


def test_non_final_chunked_coding(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Transfer-Encoding where chunked is not final is rejected."""
    req = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Transfer-Encoding: chunked, gzip\r\n"
        b"\r\n"
        b"5\r\nhello\r\n"
        b"0\r\n\r\n"
    )
    statuses = read_all_statuses_on_close(
        addr,
        req + b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n",
    )
    if not statuses:
        return False, "No response"
    if statuses[0] != 400:
        return False, f"Expected first status 400, got {statuses[0]}"
    if len(statuses) == 1:
        return True
    return False, f"Expected close before second response, got statuses {statuses}"


def test_conflicting_content_length(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Conflicting duplicate Content-Length values are rejected."""
    data = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Length: 5\r\n"
        b"Content-Length: 7\r\n"
        b"\r\n"
        b"hello!!"
    )
    resp = send_recv(addr, data)
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def test_content_length_list_same_value(
    addr: tuple[str, int],
) -> bool | tuple[bool, str]:
    """A list-form Content-Length with the same value is accepted."""
    req = b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5, 5\r\n\r\nhello"
    resp = send_recv(addr, req)
    status = parse_status(resp)
    if is_valid_status(status) and status != 400:
        return True
    return False, f"Expected valid non-400 status, got {status}"


def test_duplicate_content_length_same_value(
    addr: tuple[str, int],
) -> bool | tuple[bool, str]:
    """Duplicate Content-Length fields with same value are accepted."""
    req = (
        b"POST / HTTP/1.1\r\n"
        b"Host: localhost\r\n"
        b"Content-Length: 5\r\n"
        b"Content-Length: 5\r\n"
        b"\r\n"
        b"hello"
    )
    resp = send_recv(addr, req)
    status = parse_status(resp)
    if is_valid_status(status) and status != 400:
        return True
    return False, f"Expected valid non-400 status, got {status}"


def test_invalid_content_length_value(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Invalid Content-Length value is rejected."""
    req = b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: xyz\r\n\r\nhello"
    resp = send_recv(addr, req)
    status = parse_status(resp)
    if status == 400:
        return True
    return False, f"Expected 400, got {status}"


def _test_invalid_chunk_sequence(
    addr: tuple[str, int], body: bytes
) -> bool | tuple[bool, str]:
    """Send an invalid chunked request followed by another request on the same socket."""
    s = connect(addr)
    s.settimeout(5)
    try:
        req = (
            b"POST / HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"\r\n" + body
        )
        follow_up = b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        s.sendall(req + follow_up)
        raw = read_until_close(s, b"")
    finally:
        close_socket(s)

    statuses = extract_status_codes(raw)
    if not statuses:
        return False, "No parseable status lines after invalid chunked request"

    if 400 in statuses:
        return True

    if len(statuses) == 1:
        return True

    return False, f"Expected a 400 or immediate close, got status sequence {statuses}"


def test_invalid_chunk_size(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Invalid chunk-size token is rejected."""
    return _test_invalid_chunk_sequence(addr, b"Z\r\nhello\r\n0\r\n\r\n")


def test_chunk_missing_terminator(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Chunk-data not followed by CRLF is rejected."""
    return _test_invalid_chunk_sequence(addr, b"5\r\nhello0\r\n\r\n")


def test_expect_continue_handling(addr: tuple[str, int]) -> bool | tuple[bool, str]:
    """Expect: 100-continue is handled via interim 100 or immediate final error."""
    s = connect(addr)
    s.settimeout(5)
    try:
        headers = (
            b"POST / HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Length: 5\r\n"
            b"Expect: 100-continue\r\n"
            b"\r\n"
        )
        s.sendall(headers)
        first = recv_one_response(s, allow_informational=True)
        first_status = parse_status(first)
        if first_status == 0:
            return False, "No response to Expect: 100-continue headers"

        if first_status == 100:
            s.sendall(b"hello")
            final = recv_one_response(s, request_method=b"POST")
            final_status = parse_status(final)
            if is_valid_status(final_status) and final_status != 100:
                return True
            return False, f"Expected final non-100 status, got {final_status}"

        if 400 <= first_status < 500:
            return True
        return False, f"Expected 100 or immediate 4xx, got {first_status}"
    finally:
        close_socket(s)


SECTION = Section(
    "Body (RFC 9112 S6-7)",
    [
        case("Chunked encoding accepted", test_chunked_encoding),
        case("Chunked + HTTP/1.0 rejected", test_chunked_http10),
        case("Chunked + Content-Length rejected", test_chunked_plus_content_length),
        case(
            "Chunked + Content-Length closes connection",
            test_chunked_plus_content_length_closes,
            strict=True,
        ),
        case("Unknown transfer-coding rejected", test_unknown_transfer_encoding),
        case("Chunked not-final coding rejected", test_non_final_chunked_coding),
        case(
            "Content-Length list with same value accepted",
            test_content_length_list_same_value,
            strict=True,
        ),
        case(
            "Duplicate Content-Length with same value accepted",
            test_duplicate_content_length_same_value,
            strict=True,
        ),
        case("Invalid Content-Length rejected", test_invalid_content_length_value),
        case("Conflicting Content-Length rejected", test_conflicting_content_length),
        case("Invalid chunk-size rejected", test_invalid_chunk_size),
        case("Missing chunk terminator rejected", test_chunk_missing_terminator),
        case("Expect: 100-continue handling", test_expect_continue_handling),
    ],
)
