"""
Tests to ensure templates comply with Content Security Policy.

CSP blocks inline event handlers like onclick, onchange, etc.
These tests scan templates to catch violations before they reach production.
"""

import re
from pathlib import Path

import pytest


# Inline event handlers that are blocked by CSP
INLINE_HANDLER_PATTERN = re.compile(
    r'\s+on(click|change|keyup|keydown|keypress|submit|load|focus|blur|input|mouseover|mouseout|mouseenter|mouseleave)=',
    re.IGNORECASE
)

# Get all HTML templates
TEMPLATE_DIR = Path(__file__).parent.parent.parent / 'templates'


def get_all_templates():
    """Return all HTML template files."""
    return list(TEMPLATE_DIR.rglob('*.html'))


@pytest.mark.parametrize('template_path', get_all_templates(), ids=lambda p: str(p.relative_to(TEMPLATE_DIR)))
def test_no_inline_event_handlers(template_path):
    """
    Ensure templates don't use inline event handlers that are blocked by CSP.

    Inline handlers like onclick="..." are blocked by Content Security Policy
    when 'unsafe-inline' is not allowed. Use addEventListener instead.

    Bad:  <button onclick="doSomething()">
    Good: <button id="myBtn"> + element.addEventListener('click', doSomething)
    """
    content = template_path.read_text(encoding='utf-8')

    matches = INLINE_HANDLER_PATTERN.findall(content)

    if matches:
        # Find line numbers for better error messages
        lines_with_handlers = []
        for i, line in enumerate(content.splitlines(), 1):
            if INLINE_HANDLER_PATTERN.search(line):
                lines_with_handlers.append(f"  Line {i}: {line.strip()[:80]}")

        pytest.fail(
            f"Found inline event handler(s) that violate CSP:\n"
            + "\n".join(lines_with_handlers)
            + "\n\nUse addEventListener instead of inline handlers."
        )


def test_template_directory_exists():
    """Verify the templates directory exists and contains files."""
    assert TEMPLATE_DIR.exists(), f"Templates directory not found: {TEMPLATE_DIR}"
    templates = get_all_templates()
    assert len(templates) > 0, "No HTML templates found"
