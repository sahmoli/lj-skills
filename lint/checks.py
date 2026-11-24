"""Dependency-free check primitives for the lj skill-suite lint harness.

Necessary-not-sufficient principle: a PASSING check does NOT prove the output is
correct; a FAILED required check proves it is wrong. (Idea borrowed 2026-06-23 from
the brycewang-stanford Auto-Empirical-Research-Skills eval-harness, CC BY-SA 4.0 —
reimplemented here from scratch in the Python standard library; no code copied.)

Two severities only:
  FAIL — blocking / hard gate (the soul: provenance, schema, un-filled template).
  WARN — advisory / non-blocking (budget, completeness, re-verify backlog).
"""
import re

FAIL = "FAIL"
WARN = "WARN"


class Finding:
    def __init__(self, severity, code, target, msg):
        self.severity, self.code, self.target, self.msg = severity, code, target, msg

    def __str__(self):
        return f"[{self.severity}] {self.code:<24} {self.target}: {self.msg}"


def section(text, header_regex):
    """Body under a markdown '## <heading>' until the next '## ' (or EOF).

    `header_regex` is matched case-insensitively against the heading text.
    Returns '' if no such heading. This is the 'section scope' that lets a check
    run over only part of a page (e.g. exclude the Sources block that legitimately
    *names* debunked defaults).
    """
    heads = list(re.finditer(r"^##\s+(.*)$", text, re.M))
    for i, m in enumerate(heads):
        if re.search(header_regex, m.group(1), re.I):
            start = m.end()
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            return text[start:end]
    return ""


def bullets(block):
    """Yield logical top-level markdown bullets, joining wrapped continuation lines."""
    cur = None
    for line in block.splitlines():
        if re.match(r"\s*[-*]\s+", line):
            if cur is not None:
                yield cur
            cur = line.strip()
        elif cur is not None and line.strip() and not line.lstrip().startswith("#"):
            cur += " " + line.strip()
        elif cur is not None:
            yield cur
            cur = None
    if cur is not None:
        yield cur


def count_headers(text):
    return len(re.findall(r"^##\s+", text, re.M))


def first_match(text, patterns):
    """Return the first regex in `patterns` that matches, plus the match, else (None, None)."""
    for p in patterns:
        m = re.search(p, text)
        if m:
            return p, m
    return None, None
