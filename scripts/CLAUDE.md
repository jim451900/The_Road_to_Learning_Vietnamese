# scripts/
> L2 | 父级: ../CLAUDE.md

## 职责
把 GEB 约束变成可执行的质量门禁：生成语料库、校验链接/孤岛/L2/L3/每日不变量。
脚本只依赖 Python 3 标准库，不引入第三方包，保证任何机器克隆后即可运行。

## 成员清单
- `build_corpus.py`: 解析唯一事实源 `01_发音系统/04_每日任务_Day01-Day15.md`，生成 `语料库/` 三个数据文件。
- `check_docs.py`: 校验断链、孤岛、L2/L3 完整性、15 天每日 10 词 5 句、无平行课程、单文件行数、语料库同步。
- `generate_audio.py`: 用 macOS `say -v Linh` 从每日任务生成 `audio/DayNN/` 兜底音频，文件不入库。
- `CLAUDE.md`: 本文件。

## 依赖与暴露
- 上游：`../01_发音系统/04_每日任务_Day01-Day15.md` 的结构化标题与词句行。
- 下游：`make corpus` 调用生成器；`make check` 调用校验器并作为提交前与 GitHub Actions 门禁；`make audio` 调用音频生成器。
- 约束：修改每日任务的标题结构或词句行格式时，必须同步修改三个脚本。

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
