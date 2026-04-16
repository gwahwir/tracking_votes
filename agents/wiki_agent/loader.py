"""Wiki loader — reads all markdown files from the wiki/ directory tree."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Root of the wiki directory, resolved relative to the repo root
_WIKI_ROOT = Path(__file__).resolve().parents[2] / "wiki"


@dataclass
class WikiPage:
    path: str          # relative path from wiki root, e.g. "entities/parties/dap.md"
    title: str         # first H1 heading, or filename stem
    content: str       # full markdown text
    last_modified: float  # Unix timestamp

    def short_excerpt(self, max_chars: int = 500) -> str:
        """Return the first max_chars characters — used for TF-IDF corpus building."""
        return self.content[:max_chars]


def load_all_pages(wiki_root: Path | None = None) -> list[WikiPage]:
    """Walk the wiki directory and load every .md file."""
    root = wiki_root or _WIKI_ROOT
    pages: list[WikiPage] = []

    for md_path in sorted(root.rglob("*.md")):
        rel = md_path.relative_to(root).as_posix()
        # Skip the ingest log and index — they're operational files, not knowledge
        if rel in ("log.md", "index.md", "schema.md"):
            continue
        try:
            text = md_path.read_text(encoding="utf-8")
            title = _extract_title(text) or md_path.stem
            pages.append(WikiPage(
                path=rel,
                title=title,
                content=text,
                last_modified=md_path.stat().st_mtime,
            ))
        except OSError:
            pass

    return pages


def load_page(rel_path: str, wiki_root: Path | None = None) -> WikiPage | None:
    """Load a single wiki page by its relative path."""
    root = wiki_root or _WIKI_ROOT
    full = root / rel_path
    if not full.exists():
        return None
    text = full.read_text(encoding="utf-8")
    return WikiPage(
        path=rel_path,
        title=_extract_title(text) or full.stem,
        content=text,
        last_modified=full.stat().st_mtime,
    )


def write_page(rel_path: str, content: str, wiki_root: Path | None = None) -> None:
    """Overwrite (or create) a wiki page."""
    root = wiki_root or _WIKI_ROOT
    full = root / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def append_log(entry: str, wiki_root: Path | None = None) -> None:
    """Append a timestamped entry to wiki/log.md."""
    root = wiki_root or _WIKI_ROOT
    log_path = root / "log.md"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n{entry}\n")


def update_index(pages: list[WikiPage], wiki_root: Path | None = None) -> None:
    """Regenerate wiki/index.md from the current page list."""
    from datetime import date

    root = wiki_root or _WIKI_ROOT
    lines = [
        "# Wiki Index — Johor Election Dashboard",
        "",
        f"Last updated: {date.today().isoformat()}",
        "",
        "---",
        "",
    ]
    # Group by top-level directory
    groups: dict[str, list[WikiPage]] = {}
    for p in pages:
        top = p.path.split("/")[0]
        groups.setdefault(top, []).append(p)

    for section, section_pages in sorted(groups.items()):
        lines.append(f"## {section.title()}")
        lines.append("")
        for pg in sorted(section_pages, key=lambda x: x.path):
            lines.append(f"- [{pg.title}]({pg.path})")
        lines.append("")

    (root / "index.md").write_text("\n".join(lines), encoding="utf-8")


def _extract_title(text: str) -> str:
    """Return the first # heading from markdown text."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""
