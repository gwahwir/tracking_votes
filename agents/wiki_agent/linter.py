"""Wiki linter — checks all pages for contradictions, staleness, and orphan links."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .loader import WikiPage, load_all_pages

_CONTRADICTION_RE = re.compile(r"\[CONTRADICTION\]", re.IGNORECASE)
_DATE_RE = re.compile(r"\[Source:.*?(\d{4})\]")
_LINK_RE = re.compile(r"\[.*?\]\(([^)]+\.md)\)")


@dataclass
class LintIssue:
    level: str       # "error" | "warning" | "info"
    page_path: str
    message: str


@dataclass
class LintReport:
    issues: list[LintIssue] = field(default_factory=list)
    pages_checked: int = 0

    def has_errors(self) -> bool:
        return any(i.level == "error" for i in self.issues)

    def summary(self) -> str:
        errors = sum(1 for i in self.issues if i.level == "error")
        warnings = sum(1 for i in self.issues if i.level == "warning")
        return (
            f"Lint: {self.pages_checked} pages checked. "
            f"{errors} error(s), {warnings} warning(s)."
        )

    def to_dict(self) -> dict:
        return {
            "pages_checked": self.pages_checked,
            "issues": [
                {"level": i.level, "page": i.page_path, "message": i.message}
                for i in self.issues
            ],
            "summary": self.summary(),
        }


def lint_wiki(pages: list[WikiPage] | None = None) -> LintReport:
    """Run all lint checks and return a LintReport."""
    if pages is None:
        pages = load_all_pages()

    report = LintReport(pages_checked=len(pages))
    all_paths = {p.path for p in pages}

    current_year = datetime.now(timezone.utc).year

    for page in pages:
        # 1. Unflagged contradictions already in the text
        contradiction_count = len(_CONTRADICTION_RE.findall(page.content))
        if contradiction_count:
            report.issues.append(LintIssue(
                level="error",
                page_path=page.path,
                message=f"Contains {contradiction_count} [CONTRADICTION] marker(s) requiring human review",
            ))

        # 2. Stale citations (sources more than 2 years old)
        for match in _DATE_RE.finditer(page.content):
            year = int(match.group(1))
            if current_year - year > 2:
                report.issues.append(LintIssue(
                    level="warning",
                    page_path=page.path,
                    message=f"Citation from {year} may be stale — verify currency",
                ))
                break  # one warning per page is enough

        # 3. Orphan internal links
        for match in _LINK_RE.finditer(page.content):
            linked = match.group(1)
            # Normalise: remove leading "./" and resolve relative path
            linked = linked.lstrip("./")
            if linked not in all_paths:
                report.issues.append(LintIssue(
                    level="warning",
                    page_path=page.path,
                    message=f"Broken internal link: {linked}",
                ))

        # 4. Pages that exceed the 300-line cap
        line_count = page.content.count("\n")
        if line_count > 300:
            report.issues.append(LintIssue(
                level="warning",
                page_path=page.path,
                message=f"Page exceeds 300-line cap ({line_count} lines) — consider archiving older content",
            ))

    return report
