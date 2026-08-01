"""Tests for the repository English-only gate."""

import unittest

from scripts.check_english_only import contains_han


class EnglishOnlyGateTests(unittest.TestCase):
    def test_detects_common_and_extended_han_characters(self):
        self.assertTrue(contains_han(f"prefix {chr(0x4E2D)} suffix"))
        self.assertTrue(contains_han("path/\U00020000.txt"))

    def test_allows_english_and_non_han_symbols(self):
        self.assertFalse(contains_han("MiroFish - predict anything"))
        self.assertFalse(contains_han("README-EN.md | >=22.12 | 🐟"))


if __name__ == "__main__":
    unittest.main()
