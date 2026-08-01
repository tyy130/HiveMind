#!/usr/bin/env python3
"""Fail when tracked paths or UTF-8 text files contain Han characters."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


HAN_PATTERN = re.compile(
    "[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
    "\U00020000-\U0002fa1f]"
)


def contains_han(value: str) -> bool:
    """Return whether a string contains a Han code point."""

    return HAN_PATTERN.search(value) is not None


def tracked_paths(repository: Path) -> list[str]:
    """Return repository-relative paths currently tracked by Git."""

    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [path for path in result.stdout.decode("utf-8").split("\0") if path]


def scan_repository(repository: Path) -> list[str]:
    """Return readable violations for tracked paths and UTF-8 text content."""

    violations: list[str] = []
    for relative_path in tracked_paths(repository):
        if contains_han(relative_path):
            violations.append(f"path: {relative_path}")

        path = repository / relative_path
        if not path.is_file():
            continue

        data = path.read_bytes()
        if b"\0" in data:
            continue

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if contains_han(line):
                violations.append(f"content: {relative_path}:{line_number}")

    return violations


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    violations = scan_repository(repository)
    if violations:
        print("English-only check failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("English-only check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
