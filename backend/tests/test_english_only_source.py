"""Regression checks for the backend's English-only source policy."""

import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).parents[1]
SKIPPED_DIRECTORIES = {".pytest_cache", ".venv", "__pycache__"}
TEXT_SUFFIXES = {".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
HAN_PATTERN = re.compile(
    f"[{chr(0x3400)}-{chr(0x4DBF)}"
    f"{chr(0x4E00)}-{chr(0x9FFF)}"
    f"{chr(0xF900)}-{chr(0xFAFF)}]"
)
UNICODE_ESCAPE_PATTERN = re.compile(r"\\u([0-9a-fA-F]{4})")


def _backend_paths():
    for path in BACKEND_ROOT.rglob("*"):
        if any(part in SKIPPED_DIRECTORIES for part in path.parts):
            continue
        yield path


def _is_han_codepoint(codepoint: int) -> bool:
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
    )


def test_backend_source_and_paths_are_english_only():
    violations = []

    for path in _backend_paths():
        relative_path = path.relative_to(BACKEND_ROOT)
        if HAN_PATTERN.search(str(relative_path)):
            violations.append(f"Han characters in path: {relative_path}")

        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), 1):
            if HAN_PATTERN.search(line):
                violations.append(f"Han characters in {relative_path}:{line_number}")

            escaped_han = any(
                _is_han_codepoint(int(match.group(1), 16))
                for match in UNICODE_ESCAPE_PATTERN.finditer(line)
            )
            if escaped_han:
                violations.append(f"Escaped Han character in {relative_path}:{line_number}")

    assert not violations, "\n".join(violations)
