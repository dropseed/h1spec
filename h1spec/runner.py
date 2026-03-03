"""Test infrastructure and output formatting."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Union

# Colors
GREEN = "\033[32m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

TestFn = Callable[[tuple[str, int]], Union[bool, tuple[bool, str]]]


@dataclass(frozen=True)
class TestResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class TestCase:
    name: str
    fn: TestFn
    strict: bool = False
    hardening: bool = False


@dataclass(frozen=True)
class Section:
    name: str
    tests: list[TestCase]


def case(
    name: str,
    fn: TestFn,
    *,
    strict: bool = False,
    hardening: bool = False,
) -> TestCase:
    return TestCase(name=name, fn=fn, strict=strict, hardening=hardening)


def run_test(
    name: str,
    fn: TestFn,
    addr: tuple[str, int],
) -> TestResult:
    try:
        result = fn(addr)
        if isinstance(result, tuple):
            passed, detail = result
        else:
            passed = result
            detail = ""
        return TestResult(name, passed, detail)
    except Exception as e:
        return TestResult(name, False, f"Exception: {e}")


def _section_selected(name: str, filters: list[str]) -> bool:
    if not filters:
        return True
    lowered = name.lower()
    return any(token.lower() in lowered for token in filters)


def _case_selected(
    test_case: TestCase, *, strict: bool, include_hardening: bool
) -> bool:
    if test_case.strict and not strict:
        return False
    if test_case.hardening and not include_hardening:
        return False
    return True


def run(
    sections: list[Section],
    addr: tuple[str, int],
    *,
    strict: bool = False,
    include_hardening: bool = True,
    section_filters: list[str] | None = None,
) -> int:
    """Run all conformance tests. Returns 0 if all pass, 1 otherwise."""
    passed = 0
    failed = 0
    num = 0
    section_filters = section_filters or []

    print(f"\n{BOLD}HTTP/1.1 Conformance (RFC 9112){RESET}\n")

    for section in sections:
        if not _section_selected(section.name, section_filters):
            continue

        active_tests = [
            t
            for t in section.tests
            if _case_selected(t, strict=strict, include_hardening=include_hardening)
        ]
        if not active_tests:
            continue

        print(f"{BOLD}{section.name}{RESET}")
        for test_case in active_tests:
            num += 1
            result = run_test(test_case.name, test_case.fn, addr)
            if result.passed:
                passed += 1
                print(f"  {GREEN}\u2713{RESET} {num}. {test_case.name}")
            else:
                failed += 1
                print(f"  {RED}\u2717{RESET} {num}. {test_case.name}")
                if result.detail:
                    print(f"      {DIM}{result.detail}{RESET}")
        print()

    if num == 0:
        print(f"{RED}No tests matched filters{RESET}")
        return 2

    total = passed + failed
    if failed == 0:
        print(f"{GREEN}{passed}/{total} passed{RESET}")
    else:
        print(f"{RED}{passed}/{total} passed, {failed} failed{RESET}")

    return 1 if failed else 0
