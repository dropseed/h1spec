"""Test sections registry."""

from __future__ import annotations

from ..runner import Section
from .body import SECTION as body_section
from .connection import SECTION as connection_section
from .hardening import SECTION as hardening_section
from .headers import SECTION as headers_section
from .request_line import SECTION as request_line_section
from .response import SECTION as response_section

SECTIONS: list[Section] = [
    request_line_section,
    headers_section,
    body_section,
    response_section,
    connection_section,
    hardening_section,
]
