"""Low-level socket I/O and HTTP response parsing."""

from __future__ import annotations

import re
import socket

_SOCKET_READ_BUFFERS: dict[int, bytes] = {}
_STATUS_RE = re.compile(rb"HTTP/\d\.\d\s+(\d{3})")


# ---------------------------------------------------------------------------
# Socket helpers
# ---------------------------------------------------------------------------


def connect(addr: tuple[str, int]) -> socket.socket:
    """Create a connected TCP socket."""
    return socket.create_connection(addr, timeout=5)


def close_socket(s: socket.socket) -> None:
    """Close a socket and clear any buffered unread bytes."""
    _SOCKET_READ_BUFFERS.pop(s.fileno(), None)
    s.close()


def send_recv(addr: tuple[str, int], data: bytes, *, timeout: float = 5) -> bytes:
    """Send raw bytes, half-close write side, read until server closes."""
    s = connect(addr)
    s.settimeout(timeout)
    try:
        try:
            s.sendall(data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        try:
            s.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        chunks: list[bytes] = []
        try:
            while chunk := s.recv(4096):
                chunks.append(chunk)
        except (TimeoutError, OSError):
            pass
        return b"".join(chunks)
    finally:
        close_socket(s)


def _read_line_from_buffer(s: socket.socket, buf: bytes) -> tuple[bytes, bytes, bool]:
    """Read one CRLF-terminated line from a socket-backed buffer."""
    try:
        while b"\r\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                return b"", buf, False
            buf += chunk
    except (TimeoutError, OSError):
        return b"", buf, False

    line, buf = buf.split(b"\r\n", 1)
    return line, buf, True


def _read_chunked_from_buffer(s: socket.socket, buf: bytes) -> tuple[bytes, bytes]:
    """Read a chunked payload (including trailers) from a socket-backed buffer."""
    body = bytearray()

    while True:
        line, buf, ok = _read_line_from_buffer(s, buf)
        if not ok:
            return bytes(body), buf
        body.extend(line + b"\r\n")

        size_token = line.split(b";", 1)[0].strip()
        try:
            size = int(size_token, 16)
        except ValueError:
            return bytes(body), buf

        if size == 0:
            while True:
                trailer_line, buf, ok = _read_line_from_buffer(s, buf)
                if not ok:
                    return bytes(body), buf
                body.extend(trailer_line + b"\r\n")
                if trailer_line == b"":
                    return bytes(body), buf

        needed = size + 2  # chunk-data + terminating CRLF
        try:
            while len(buf) < needed:
                chunk = s.recv(4096)
                if not chunk:
                    body.extend(buf)
                    return bytes(body), b""
                buf += chunk
        except (TimeoutError, OSError):
            body.extend(buf)
            return bytes(body), b""

        body.extend(buf[:needed])
        buf = buf[needed:]


def _read_content_length_body(
    s: socket.socket, buf: bytes, content_length: int
) -> tuple[bytes, bytes]:
    """Read exactly Content-Length bytes from a socket-backed buffer."""
    try:
        while len(buf) < content_length:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
    except (TimeoutError, OSError):
        pass
    return buf[:content_length], buf[content_length:]


def read_until_close(s: socket.socket, buf: bytes) -> bytes:
    """Read bytes until the peer closes the connection."""
    parts = [buf]
    try:
        while chunk := s.recv(4096):
            parts.append(chunk)
    except (TimeoutError, OSError):
        pass
    return b"".join(parts)


def recv_one_response(
    s: socket.socket,
    *,
    allow_informational: bool = False,
    request_method: bytes | None = None,
) -> bytes:
    """Read one HTTP response while preserving unread bytes for the next call."""
    key = s.fileno()
    buf = _SOCKET_READ_BUFFERS.pop(key, b"")

    while True:
        try:
            while b"\r\n\r\n" not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    _SOCKET_READ_BUFFERS[key] = b""
                    return buf
                buf += chunk
        except (TimeoutError, OSError):
            _SOCKET_READ_BUFFERS[key] = buf
            return b""

        header_blob, buf = buf.split(b"\r\n\r\n", 1)
        raw_head = header_blob + b"\r\n\r\n"
        status = parse_status(raw_head)
        headers = parse_headers(raw_head)

        no_body = (
            request_method == b"HEAD" or 100 <= status < 200 or status in (204, 304)
        )
        body = b""
        if not no_body:
            if is_chunked(headers):
                body, buf = _read_chunked_from_buffer(s, buf)
            else:
                content_length = parse_content_length(headers)
                if content_length is not None:
                    body, buf = _read_content_length_body(s, buf, content_length)
                elif has_close_token(headers.get(b"connection", b"")):
                    body = read_until_close(s, buf)
                    buf = b""

        response = raw_head + body

        if 100 <= status < 200 and status != 101 and not allow_informational:
            continue

        _SOCKET_READ_BUFFERS[key] = buf
        return response


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_status(response: bytes) -> int:
    """Extract HTTP status code from a raw response."""
    if not response:
        return 0
    first_line = response.split(b"\r\n")[0]
    parts = first_line.split(b" ", 2)
    if len(parts) < 2:
        return 0
    try:
        return int(parts[1])
    except ValueError:
        return 0


def parse_headers(response: bytes) -> dict[bytes, bytes]:
    """Extract headers as {lowercase-name: value} from a raw response."""
    header_end = response.find(b"\r\n\r\n")
    if header_end < 0:
        return {}
    headers: dict[bytes, bytes] = {}
    for line in response[:header_end].split(b"\r\n")[1:]:
        if b":" in line:
            name, _, value = line.partition(b":")
            headers[name.strip().lower()] = value.strip()
    return headers


def get_body(response: bytes) -> bytes:
    """Return everything after the header section."""
    idx = response.find(b"\r\n\r\n")
    if idx < 0:
        return b""
    return response[idx + 4 :]


def parse_content_length(headers: dict[bytes, bytes]) -> int | None:
    value = headers.get(b"content-length")
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def is_chunked(headers: dict[bytes, bytes]) -> bool:
    value = headers.get(b"transfer-encoding", b"")
    return b"chunked" in value.lower()


def has_close_token(value: bytes) -> bool:
    return any(token.strip().lower() == b"close" for token in value.split(b","))


def is_valid_status(status: int) -> bool:
    return 100 <= status <= 599


def extract_status_codes(data: bytes) -> list[int]:
    return [int(m.group(1)) for m in _STATUS_RE.finditer(data)]


def response_signals_close(response: bytes) -> bool:
    headers = parse_headers(response)
    return has_close_token(headers.get(b"connection", b""))


def read_all_statuses_on_close(
    addr: tuple[str, int], payload: bytes, *, timeout: float = 5
) -> list[int]:
    s = connect(addr)
    s.settimeout(timeout)
    try:
        s.sendall(payload)
        raw = read_until_close(s, b"")
    finally:
        close_socket(s)
    return extract_status_codes(raw)
