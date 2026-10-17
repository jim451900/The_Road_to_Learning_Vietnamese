#!/usr/bin/env python3
"""Build the derived corpus views from the single daily-task source.

[INPUT]: ../01_发音系统/04_每日任务_Day01-Day15.md
[OUTPUT]: ../语料库/01_词表.md, 02_句库.md, 03_音点表.md
[POS]: GEB 文档系统的派生层生成器；check_docs.py 复用本模块的解析与生成结果
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / "01_发音系统" / "04_每日任务_Day01-Day15.md"
OUT_DIR = ROOT / "语料库"

DAY_RE = re.compile(r"^##\s+Day(\d+)\s*(.*)$")
SECTION_RE = re.compile(r"^###\s+(.+?)\s*$")
META_RE = re.compile(r"^>\s*([^：:]+)[：:]\s*(.*)$")
ITEM_RE = re.compile(r"^-\s+`([^`]+)`\s*/\s*(.*)$")


def parse_item(line: str) -> dict | None:
    """Parse one backticked VI / CN / EN line."""
    match = ITEM_RE.match(line)
    if not match:
        return None
    vi = match.group(1).strip()
    rest = match.group(2).strip()
    parts = rest.split(" / ")
    cn = parts[0].strip()
    en = " / ".join(parts[1:]).strip()
    return {"vi": vi, "cn": cn, "en": en}


def parse_daily(path: Path = DAILY) -> list[dict]:
    """Parse the canonical daily file into structured day records."""
    days: list[dict] = []
    current: dict | None = None
    section: str | None = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        day_match = DAY_RE.match(line)
        if day_match:
            current = {
                "num": int(day_match.group(1)),
                "title": day_match.group(2).strip(),
                "meta": {},
                "drill": [],
                "words": [],
                "sentences": [],
                "scene_lines": [],
            }
            days.append(current)
            section = None
            continue

        if current is None:
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            section = section_match.group(1).strip()
            continue

        if section is None:
            meta_match = META_RE.match(line)
            if meta_match:
                current["meta"][meta_match.group(1).strip()] = meta_match.group(2).strip()
            continue

        if section in {"发音 drill", "高频词", "实用句"} and line.startswith("- `"):
            item = parse_item(line)
            if item:
                key = {"发音 drill": "drill", "高频词": "words", "实用句": "sentences"}[section]
                current[key].append(item)
            continue

        if section == "微场景" and line.strip():
            current["scene_lines"].append(line.strip())

    for day in days:
        day["scene"] = " ".join(day["scene_lines"]).strip()
        del day["scene_lines"]

    return days


def slugify(text: str) -> str:
    """ASCII slug for audio file names."""
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "item"


def _cell(text: str) -> str:
    """Escape a Markdown table cell."""
    return text.replace("|", r"\|")


def _header(output: str, pos: str) -> str:
    return (
        "<!--\n"
        "[INPUT]: 由 scripts/build_corpus.py 解析 ../01_发音系统/04_每日任务_Day01-Day15.md 生成\n"
        f"[OUTPUT]: {output}\n"
        f"[POS]: {pos}\n"
        "[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md\n"
        "-->\n"
    )


def build() -> dict[str, str]:
    """Return {relative output path: content} for all generated corpus files."""
    days = parse_daily()

    words: dict[str, dict] = {}
    sentences: dict[str, dict] = {}

    for day in days:
        for index, word in enumerate(day["words"], start=1):
            key = word["vi"].lower()
            if key not in words:
                words[key] = {
                    "id": f"W{day['num']:02d}-{index:02d}",
                    "vi": word["vi"],
                    "cn": word["cn"],
                    "en": word["en"],
                    "first_day": day["num"],
                    "count": 0,
                    "days": [],
                }
            entry = words[key]
            entry["count"] += 1
            if day["num"] not in entry["days"]:
                entry["days"].append(day["num"])

        for index, sentence in enumerate(day["sentences"], start=1):
            key = sentence["vi"].lower()
            if key not in sentences:
                sentences[key] = {
                    "id": f"S{day['num']:02d}-{index:02d}",
                    "vi": sentence["vi"],
                    "cn": sentence["cn"],
                    "en": sentence["en"],
                    "first_day": day["num"],
                    "days": [],
                    "tag": day["meta"].get("音点", ""),
                }
            entry = sentences[key]
            if day["num"] not in entry["days"]:
                entry["days"].append(day["num"])

    word_lines = [
        _header(
            "对外提供 15 天课程去重后的词条索引，含首次出现、出现次数与出现 Day",
            "语料库 的派生视图；由每日任务生成，禁止手改",
        ),
        "# 词表（自动生成）",
        "",
        "> 生成命令：`make corpus`；校验命令：`make check`。禁止手改本文件。",
        f"> 共 {len(words)} 个唯一词条。",
        "",
        "| ID | 越南语 | 中文 | English | 首次出现 | 出现次数 | 出现 Day |",
        "|---|---|---|---|---|---|---|",
    ]
    for entry in words.values():
        days_text = ", ".join(f"Day{num:02d}" for num in entry["days"])
        word_lines.append(
            f"| {entry['id']} | `{_cell(entry['vi'])}` | {_cell(entry['cn'])} | "
            f"{_cell(entry['en'])} | Day{entry['first_day']:02d} | {entry['count']} | {days_text} |"
        )

    sentence_lines = [
        _header(
            "对外提供 15 天课程去重后的句子索引，含稳定 ID、Day 与音点标签",
            "语料库 的派生视图；02_句子积木 只引用本表 ID，不重抄整句",
        ),
        "# 句库（自动生成）",
        "",
        "> 生成命令：`make corpus`；校验命令：`make check`。禁止手改本文件。",
        f"> 共 {len(sentences)} 个唯一句子。ID 规则：`S{{Day}}-{{序号}}`。",
        "",
        "| ID | 越南语 | 中文 | English | Day | 标签 |",
        "|---|---|---|---|---|---|",
    ]
    for entry in sentences.values():
        days_text = ", ".join(f"Day{num:02d}" for num in entry["days"])
        sentence_lines.append(
            f"| {entry['id']} | `{_cell(entry['vi'])}` | {_cell(entry['cn'])} | "
            f"{_cell(entry['en'])} | {days_text} | {_cell(entry['tag'])} |"
        )

    point_lines = [
        _header(
            "对外提供 15 天音点、发音 drill、常见错误与最小对立对照表",
            "语料库 的派生视图；听辨与纠偏时按 Day 查询",
        ),
        "# 音点表（自动生成）",
        "",
        "> 生成命令：`make corpus`；校验命令：`make check`。禁止手改本文件。",
        "",
        "| Day | 音点 | 发音 drill | 常见错误 | 最小对立 |",
        "|---|---|---|---|---|",
    ]
    for day in days:
        drill = "、".join(f"`{_cell(item['vi'])}`" for item in day["drill"])
        point_lines.append(
            f"| Day{day['num']:02d} | {_cell(day['meta'].get('音点', ''))} | {drill} | "
            f"{_cell(day['meta'].get('常见错误', ''))} | {_cell(day['meta'].get('最小对立', ''))} |"
        )

    return {
        "01_词表.md": "\n".join(word_lines) + "\n",
        "02_句库.md": "\n".join(sentence_lines) + "\n",
        "03_音点表.md": "\n".join(point_lines) + "\n",
    }


def write() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in build().items():
        path = OUT_DIR / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def check() -> list[str]:
    """Return a list of stale/missing generated files."""
    problems = []
    for name, content in build().items():
        path = OUT_DIR / name
        if not path.exists():
            problems.append(f"missing generated file: {path.relative_to(ROOT)}")
        elif path.read_text(encoding="utf-8") != content:
            problems.append(f"stale generated file: {path.relative_to(ROOT)} (run make corpus)")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Build derived corpus views.")
    parser.add_argument("--check", action="store_true", help="only check whether files are up to date")
    args = parser.parse_args()

    if args.check:
        problems = check()
        for problem in problems:
            print(f"ERROR: {problem}")
        if problems:
            return 1
        print("corpus is up to date")
        return 0

    written = write()
    for path in written:
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
