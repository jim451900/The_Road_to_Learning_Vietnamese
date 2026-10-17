#!/usr/bin/env python3
"""Enforce the GEB document contract for this repository.

[INPUT]: 全部 Markdown 文件、../01_发音系统/04_每日任务_Day01-Day15.md、build_corpus.py
[OUTPUT]: 退出码 0/1 与错误清单；零断链、零孤岛、L2/L3 完整、15 天不变量、语料库同步
[POS]: scripts 的质量门禁；make check 调用本脚本，提交前必须通过
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

import build_corpus

ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / "01_发音系统" / "04_每日任务_Day01-Day15.md"

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
DAY_HEADING_RE = re.compile(r"^##\s+Day\d+", re.M)
S_ID_RE = re.compile(r"\bS\d{2}-\d{2}\b")
W_ID_RE = re.compile(r"\bW\d{2}-\d{2}\b")
L3_TAGS = ("[INPUT]", "[OUTPUT]", "[POS]", "[PROTOCOL]")
CORPUS_DIR = ROOT / "语料库"


def md_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts
    )


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def check_links(files: list[Path]) -> list[str]:
    errors = []
    for path in files:
        base = path.parent
        for match in LINK_RE.finditer(path.read_text(encoding="utf-8")):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            target = urllib.parse.unquote(target)
            resolved = (base / target).resolve()
            if not resolved.exists():
                errors.append(f"broken link: {rel(path)} -> {match.group(1)}")
    return errors


def check_l2(files: list[Path]) -> list[str]:
    errors = []
    dirs = sorted({path.parent for path in files if path.parent != ROOT})
    for directory in dirs:
        if not (directory / "CLAUDE.md").exists():
            errors.append(f"missing L2 map: {rel(directory)}/CLAUDE.md")
    return errors


def check_l3(files: list[Path]) -> list[str]:
    errors = []
    for path in files:
        if path.name == "CLAUDE.md":
            continue
        head = path.read_text(encoding="utf-8")[:800]
        missing = [tag for tag in L3_TAGS if tag not in head]
        if missing:
            errors.append(f"missing L3 tags {missing}: {rel(path)}")
    return errors


def check_orphans(files: list[Path]) -> list[str]:
    referenced: set[Path] = set()
    for path in files:
        base = path.parent
        for match in LINK_RE.finditer(path.read_text(encoding="utf-8")):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            referenced.add((base / urllib.parse.unquote(target)).resolve())

    errors = []
    for path in files:
        if path.name == "CLAUDE.md":
            continue
        if path.resolve() not in referenced:
            errors.append(f"orphan file (no inbound Markdown link): {rel(path)}")
    return errors


def check_daily() -> list[str]:
    errors = []
    days = build_corpus.parse_daily()
    numbers = [day["num"] for day in days]
    if numbers != list(range(1, 16)):
        errors.append(f"daily task must contain Day01-Day15 exactly once; got {numbers}")
    for day in days:
        label = f"Day{day['num']:02d}"
        if len(day["words"]) != 10:
            errors.append(f"{label}: expected 10 words, got {len(day['words'])}")
        if len(day["sentences"]) != 5:
            errors.append(f"{label}: expected 5 sentences, got {len(day['sentences'])}")
        if len(day["drill"]) < 3:
            errors.append(f"{label}: expected at least 3 drill items, got {len(day['drill'])}")
        if not day["scene"]:
            errors.append(f"{label}: missing micro-scene")
        for key in ("音点", "常见错误", "最小对立"):
            if not day["meta"].get(key):
                errors.append(f"{label}: missing metadata '{key}'")
    return errors


def check_corpus_ids(files: list[Path]) -> list[str]:
    """Every S/W ID referenced in prose must exist in the generated corpus."""
    word_table = CORPUS_DIR / "01_词表.md"
    sentence_table = CORPUS_DIR / "02_句库.md"
    known = set()
    known |= set(re.findall(r"^\| (W\d{2}-\d{2}) \|", word_table.read_text(encoding="utf-8"), re.M))
    known |= set(re.findall(r"^\| (S\d{2}-\d{2}) \|", sentence_table.read_text(encoding="utf-8"), re.M))

    generated = set(CORPUS_DIR.glob("*.md"))
    errors = []
    for path in files:
        if path in generated:
            continue
        text = path.read_text(encoding="utf-8")
        for ref in sorted(set(S_ID_RE.findall(text)) | set(W_ID_RE.findall(text))):
            if ref not in known:
                errors.append(f"unknown corpus ID {ref} in {rel(path)}")
    return errors


def check_no_parallel_days(files: list[Path]) -> list[str]:
    errors = []
    for path in files:
        if path == DAILY:
            continue
        text = path.read_text(encoding="utf-8")
        if DAY_HEADING_RE.search(text) and ("### 高频词" in text or "### 实用句" in text):
            errors.append(f"parallel daily curriculum detected in {rel(path)}")
    return errors


def check_file_sizes(files: list[Path]) -> list[str]:
    errors = []
    for path in files:
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > 800:
            errors.append(f"file exceeds 800 lines ({count}): {rel(path)}")
    return errors


def main() -> int:
    files = md_files()
    errors: list[str] = []
    errors += check_links(files)
    errors += check_l2(files)
    errors += check_l3(files)
    errors += check_orphans(files)
    errors += check_daily()
    errors += check_corpus_ids(files)
    errors += check_no_parallel_days(files)
    errors += check_file_sizes(files)
    errors += build_corpus.check()

    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"OK: {len(files)} Markdown files, links/L2/L3/orphans/daily/corpus all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
