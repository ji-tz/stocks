"""
Unit tests for the workflow-enforcer keyword matching pattern (Issue #219).

Tests the regex used in .github/workflows/workflow-enforcer.yml step 2️⃣ Issue 关联.

Pattern (from design doc):
    (close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)[[:space:]]+#[0-9]+

Matching logic (from workflow-enforcer):
    1. Check BODY first — if match, success
    2. Then check TITLE — if match, success
    3. Neither matched — failure
    4. All checks are case-insensitive
"""

import re
import pytest

# The exact regex from .github/workflows/workflow-enforcer.yml step 2
# POSIX [[:space:]]+ → Python \s+ (matches space, tab, newline, etc.)
KEYWORD_PATTERN = r'(close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+#[0-9]+'

# Compiled case-insensitive pattern for existence check
_re_match = re.compile(KEYWORD_PATTERN, re.IGNORECASE)

# Compiled case-insensitive pattern for extraction
_re_extract = re.compile(KEYWORD_PATTERN, re.IGNORECASE)


def check_keyword_match(text: str) -> list[str]:
    """Return list of matched patterns if any, else empty list."""
    return _re_extract.findall(text)


def has_keyword_match(text: str) -> bool:
    """Return True if text contains a keyword-issue reference."""
    return bool(_re_match.search(text))


def check_pr_issue_association(body: str, title: str) -> tuple[bool, str, list[str]]:
    """
    Simulate the workflow-enforcer step 2 logic.

    Returns (matched, source, matches):
        matched: True if any match found
        source: 'body', 'title', or ''
        matches: list of matched patterns (full match strings)
    """
    body_matches = _re_extract.findall(body)
    if body_matches:
        return (True, 'body', [m[0] + ' #...' for m in body_matches])

    title_matches = _re_extract.findall(title)
    if title_matches:
        return (True, 'title', [m[0] + ' #...' for m in title_matches])

    return (False, '', [])


# ─── Test case data ──────────────────────────────────────────────

# Each case: (text, should_match, description)
MATCH_CASES = [
    # === Keyword variants (all 9) ===
    ("close #123",     True,  "keyword: close"),
    ("closes #123",    True,  "keyword: closes"),
    ("closed #123",    True,  "keyword: closed"),
    ("fix #123",       True,  "keyword: fix"),
    ("fixes #123",     True,  "keyword: fixes"),
    ("fixed #123",     True,  "keyword: fixed"),
    ("resolve #123",   True,  "keyword: resolve"),
    ("resolves #123",  True,  "keyword: resolves"),
    ("resolved #123",  True,  "keyword: resolved"),

    # === Case-insensitive ===
    ("Close #123",     True,  "case: title case Close"),
    ("CLOSE #123",     True,  "case: uppercase CLOSE"),
    ("Fixes #123",     True,  "case: capitalized Fixes"),
    ("FIXED #123",     True,  "case: uppercase FIXED"),
    ("Resolve #123",   True,  "case: title case Resolve"),
    ("rEsOlVe #123",   True,  "case: mixed case rEsOlVe"),

    # === Various whitespace ===
    ("close  #123",    True,  "space: double space"),
    ("close   #123",   True,  "space: triple space"),
    ("close\t#123",    True,  "space: tab delimiter"),

    # === Multiple issues ===
    ("fix #123, close #456",              True, "multiple: comma separated"),
    ("close #123 #456",                   True, "multiple: space separated"),
    ("fix #123 and resolve #456",         True, "multiple: 'and' separated"),
    ("fix #123\nclose #456",              True, "multiple: newline separated"),

    # === Context around the match ===
    ("This PR fixes #123",               True,  "context: prefix text"),
    ("Related: closes #456",             True,  "context: prefix with colon"),
    ("close #123 and done",              True,  "context: suffix text"),
    ("## Summary\nfixes #789\n## Notes", True,  "context: multiline body"),
]

NO_MATCH_CASES = [
    # === No keyword ===
    ("#123",              False, "bare issue ref no keyword"),
    ("ref #123",          False, "ref keyword not recognized"),
    ("see #123",          False, "see keyword not recognized"),
    ("related #123",      False, "related not recognized"),
    ("",                  False, "empty string"),

    # === Similar but not keyword + issue ===
    ("closedoor #123",    False, "fused word: closedoor"),
    ("closure #123",      False, "fused word: closure"),
    ("fixedin #123",      False, "fused word: fixedin"),
    ("resolve_issue",     False, "no issue number"),
    ("fixed in #123",     False, "separated: fixed in #123"),

    # === Missing space before issue number ===
    ("close#123",         False, "no space: close#123"),
    ("fix#123",           False, "no space: fix#123"),
    ("resolved#123",      False, "no space: resolved#123"),

    # === Non-numeric issue number ===
    ("close #abc",        False, "non-numeric: close #abc"),
    ("fix #ABC",          False, "non-numeric: fix #ABC"),
    ("resolved #12a",     True,  "non-numeric: resolved #12a — grep matches #12 as valid number, 'a' is trailing"),

    # === Wrong keyword format ===
    ("close# 123",        False, "space after hash: close# 123"),
    ("close # -1",        False, "negative number"),
    ("close # 0",         False, "zero with space after hash: # 0 has a space, doesn't match [0-9]+"),
]


class TestKeywordMatching:
    """Tests for the regex pattern used in workflow-enforcer keyword matching."""

    @pytest.mark.parametrize("text,expected,desc", MATCH_CASES)
    def test_positive_matches(self, text, expected, desc):
        """All valid keyword-issue patterns should match."""
        result = has_keyword_match(text)
        assert result == expected, f"[{desc}] expected match=True for: {text!r}"

    @pytest.mark.parametrize("text,expected,desc", NO_MATCH_CASES)
    def test_negative_matches(self, text, expected, desc):
        """Invalid / non-keyword patterns should not match."""
        result = has_keyword_match(text)
        assert result == expected, f"[{desc}] expected match={expected} for: {text!r}"


class TestBodyTitlePriority:
    """Tests for the Body → Title priority logic."""

    def test_body_priority(self):
        """When both body and title match, body should be returned."""
        body = "fixes #456"
        title = "closes #123"
        matched, source, _ = check_pr_issue_association(body, title)
        assert matched is True
        assert source == "body"

    def test_title_fallback(self):
        """When only title matches, it should work."""
        body = "some PR description"
        title = "fixes #123"
        matched, source, _ = check_pr_issue_association(body, title)
        assert matched is True
        assert source == "title"

    def test_body_only_match(self):
        """When only body matches, it should work."""
        body = "This resolves #789"
        title = "A title without issue"
        matched, source, _ = check_pr_issue_association(body, title)
        assert matched is True
        assert source == "body"

    def test_no_match_either(self):
        """When neither matches, should return failure."""
        body = "Just some description"
        title = "PR Title"
        matched, source, _ = check_pr_issue_association(body, title)
        assert matched is False
        assert source == ""

    def test_empty_body_title_fallback(self):
        """When body is empty, still check title."""
        body = ""
        title = "close #999"
        matched, source, _ = check_pr_issue_association(body, title)
        assert matched is True
        assert source == "title"

    def test_both_empty(self):
        """When both are empty, no match."""
        body = ""
        title = ""
        matched, source, _ = check_pr_issue_association(body, title)
        assert matched is False
        assert source == ""


class TestMultipleIssues:
    """Tests for multiple Issue references in one body/title."""

    def test_two_issues_comma_separated(self):
        """fix #123, close #456 should match both."""
        matches = check_keyword_match("fix #123, close #456")
        assert len(matches) == 2, f"expected 2 matches, got {len(matches)}: {matches}"

    def test_two_issues_space_separated(self):
        """close #123 #456 — only the first has a keyword (designed: each needs independent keyword)."""
        matches = check_keyword_match("close #123 #456")
        assert len(matches) == 1, f"expected 1 match, got {len(matches)}: {matches}"
        # #456 has no independent keyword → per design, it's not matched

    def test_three_issues(self):
        """fix #1, resolve #2, close #3 should match all three."""
        matches = check_keyword_match("fix #1, resolve #2, close #3")
        assert len(matches) == 3, f"expected 3 matches, got {len(matches)}: {matches}"

    def test_duplicate_issues(self):
        """fix #123 and fix #123 should match both (duplicates allowed)."""
        matches = check_keyword_match("fix #123 and fix #123")
        assert len(matches) == 2, f"expected 2 matches, got {len(matches)}: {matches}"

    def test_mixed_case_multiple(self):
        """FIX #1, Closed #2, resolves #3 should all match."""
        matches = check_keyword_match("FIX #1, Closed #2, resolves #3")
        assert len(matches) == 3, f"expected 3 matches, got {len(matches)}: {matches}"


class TestBoundaryConditions:
    """Tests for edge cases and boundary conditions."""

    def test_issue_in_url(self):
        """URLs like https://github.com/org/repo/issues/123 should NOT match."""
        text = "see https://github.com/org/repo/issues/123"
        assert has_keyword_match(text) is False, "URL should not match keyword pattern"

    def test_code_block_with_keyword(self):
        """Keywords inside code blocks are still matched (workflow is grep-based)."""
        text = "```\nclose #123\n```"
        assert has_keyword_match(text) is True, "code block should still match"

    def test_very_long_body(self):
        """Long body should still match correctly."""
        text = "This PR " + "does stuff. " * 100 + "fixes #999 at the end."
        assert has_keyword_match(text) is True

    def test_special_chars_around(self):
        """Special characters around the keyword should not affect matching."""
        assert has_keyword_match("(fix #123)") is True
        assert has_keyword_match("[fix #123]") is True
        assert has_keyword_match("\"fix #123\"") is True
        assert has_keyword_match("'fix #123'") is True

    def test_large_issue_number(self):
        """Very large issue numbers should still work."""
        assert has_keyword_match("close #999999999") is True

    def test_no_false_positive_readme(self):
        """README or changelog references like #123 should not trigger."""
        text = "Changes in #123 and #456 from previous release"
        assert has_keyword_match(text) is False, "bare #ref without keyword"

    def test_keyword_as_part_of_longer_word(self):
        """Keywords that are part of a longer word should be checked carefully."""
        # 'closure' contains 'close' but is not the keyword
        assert has_keyword_match("closure #123") is False
        # 'fixedly' contains 'fixed' but is not the keyword
        assert has_keyword_match("fixedly #123") is False  # this depends on \b boundary
        # Our pattern uses \s+ so adjacent chars after the keyword still match
        # Actually, `fixedly #123` would match because \s+ requires whitespace
        # and 'fixed' is followed by 'ly', not whitespace.
        # Let me verify the regex behavior...
        # Actually, `fixedly #123` - the regex looks for 'fixed' followed by \s+
        # 'fixedly' has 'fixed' then 'ly' which is not \s+, so it should NOT match.
        # Let me keep this test to document the behavior.


class TestWhitespaceVariations:
    """Tests for various whitespace separators."""

    @pytest.mark.parametrize("ws", [" ", "  ", "   ", "\t", " \t", "\t ", " \t "])
    def test_various_whitespace(self, ws):
        """All whitespace separators between keyword and # should work."""
        text = f"fix{ws}#123"
        assert has_keyword_match(text) is True, f"failed with whitespace: {ws!r}"

    def test_newline_separator(self):
        """Newline between keyword and hash should also match."""
        text = "fix\n#123"
        assert has_keyword_match(text) is True
