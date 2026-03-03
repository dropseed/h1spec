"""HTTP/1.1 conformance test tool in the spirit of h2spec."""

from __future__ import annotations

import argparse
import sys

from .runner import run
from .tests import SECTIONS


def parse_target(target: str) -> tuple[str, int]:
    """Parse host:port or [ipv6-host]:port."""
    if target.startswith("["):
        end = target.find("]")
        if end < 0 or end + 1 >= len(target) or target[end + 1] != ":":
            raise ValueError("Expected [ipv6-host]:port")
        host = target[1:end]
        port = int(target[end + 2 :])
        return host, port

    host, port_str = target.rsplit(":", 1)
    return host, int(port_str)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HTTP/1.1 RFC 9112/9110 conformance checks",
    )
    parser.add_argument(
        "target",
        help="Target endpoint as host:port or [ipv6-host]:port",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Run stricter RFC edge-case tests that hardened servers sometimes reject.",
    )
    parser.add_argument(
        "--no-hardening",
        action="store_true",
        help="Skip implementation-defined hardening checks.",
    )
    parser.add_argument(
        "--section",
        action="append",
        default=[],
        metavar="TEXT",
        help="Run only sections whose title contains TEXT (repeatable).",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])
    try:
        host, port = parse_target(args.target)
    except ValueError as e:
        print(f"{e}", file=sys.stderr)
        sys.exit(2)
    sys.exit(
        run(
            SECTIONS,
            (host, port),
            strict=args.strict,
            include_hardening=not args.no_hardening,
            section_filters=args.section,
        )
    )
