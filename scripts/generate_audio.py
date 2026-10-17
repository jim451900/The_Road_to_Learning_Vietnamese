#!/usr/bin/env python3
"""Generate local fallback audio from the canonical daily task file.

[INPUT]: ../01_发音系统/04_每日任务_Day01-Day15.md 的词句，macOS `say` 与越南语语音 Linh
[OUTPUT]: ../audio/DayNN/W*.aiff、S*.aiff、all.aiff；文件被 .gitignore 忽略
[POS]: scripts 的本地音频生成器；把“先辨后说”变成可执行的听辨材料，不提交二进制
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import build_corpus

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "audio"
VOICE = "Linh"
WORD_RATE = 140
SENTENCE_RATE = 150


def require_macos_voice() -> None:
    if sys.platform != "darwin" or not shutil.which("say"):
        raise SystemExit("This script requires macOS `say`. Use a native speaker, Forvo, or another TTS on other platforms.")
    voices = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=False).stdout
    if "vi_VN" not in voices:
        raise SystemExit("Vietnamese voice `Linh` (vi_VN) is not installed. Add it in System Settings > Accessibility > Spoken Content.")


def say(text: str, output: Path, rate: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["say", "-v", VOICE, "-r", str(rate), "-o", str(output), text],
        check=True,
    )


def generate_day(day: dict) -> int:
    folder = AUDIO_DIR / f"Day{day['num']:02d}"
    count = 0

    for index, word in enumerate(day["words"], start=1):
        slug = build_corpus.slugify(word["vi"])
        output = folder / f"W{day['num']:02d}-{index:02d}_{slug}.aiff"
        say(word["vi"], output, WORD_RATE)
        count += 1

    for index, sentence in enumerate(day["sentences"], start=1):
        output = folder / f"S{day['num']:02d}-{index:02d}.aiff"
        say(sentence["vi"], output, SENTENCE_RATE)
        count += 1

    combined = " [[slnc 800]] ".join(
        [item["vi"] for item in day["words"]] + [item["vi"] for item in day["sentences"]]
    )
    say(combined, folder / "all.aiff", SENTENCE_RATE)
    count += 1

    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate local Vietnamese fallback audio.")
    parser.add_argument("--all", action="store_true", help="generate all 15 days")
    parser.add_argument("--day", type=int, action="append", help="generate one day (repeatable)")
    args = parser.parse_args()

    if not args.all and not args.day:
        parser.print_help()
        return 1

    require_macos_voice()
    days = build_corpus.parse_daily()
    selected = days if args.all else [day for day in days if day["num"] in set(args.day or [])]

    if not selected:
        print("no matching day")
        return 1

    total = 0
    for day in selected:
        count = generate_day(day)
        total += count
        print(f"Day{day['num']:02d}: {count} files")

    print(f"done: {total} files under {AUDIO_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
