#!/usr/bin/env python3
"""Run the official C-Eval CSV data against a DeepSeek chat model."""

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import random
import re
import statistics
import sys
import time
import zipfile

from eval import DEFAULT_BASE_URL, ROOT, api_json, get_key, read_jsonl


LETTERS = frozenset("ABCD")
PROMPT_VERSION = "ceval-answer-only-zero-shot-nonthinking-v2"
SYSTEM_PROMPT = "你正在参加单项选择考试。最终回答必须仅包含一个大写英文字母 A、B、C 或 D，不要解释，不要添加其他文字。"
SUBJECT_MAPPING = ROOT / "cases" / "ceval_subject_mapping.json"


def dataset_files(path, split):
    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                if f"/{split}/" in f"/{name}" and name.endswith(f"_{split}.csv"):
                    yield name, archive.read(name)
    elif path.is_dir():
        for file in sorted(path.rglob(f"*_{split}.csv")):
            if file.parent.name == split:
                yield str(file.relative_to(path)), file.read_bytes()
    else:
        raise ValueError(f"找不到 C-Eval 数据：{path}")


def load_questions(path, split):
    questions = []
    digest = hashlib.sha256()
    mapping_bytes = SUBJECT_MAPPING.read_bytes()
    mapping = json.loads(mapping_bytes)
    digest.update(mapping_bytes)
    subjects = set()
    for name, content in dataset_files(path, split):
        subject = Path(name).stem.removesuffix(f"_{split}")
        if subject not in mapping:
            raise ValueError(f"官方学科映射中找不到 {subject}")
        subjects.add(subject)
        digest.update(name.encode("utf-8") + b"\0" + content)
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        required = {"id", "question", "A", "B", "C", "D", "answer"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{name} 缺少列：{', '.join(sorted(required - set(reader.fieldnames or [])))}")
        for row in reader:
            answer = row["answer"].strip().upper()
            if answer not in LETTERS:
                raise ValueError(f"{name} 第 {row['id']} 题没有有效标准答案")
            questions.append({
                "id": f"{subject}:{row['id']}",
                "subject": subject,
                "subject_zh": mapping[subject]["name_zh"],
                "category": mapping[subject]["category"],
                "question": row["question"],
                "options": {letter: row[letter] for letter in "ABCD"},
                "answer": answer,
            })
    if not questions:
        raise ValueError(f"未在 {path} 找到 {split} 分组的官方 CSV")
    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("数据集中有重复题目 ID")
    return questions, digest.hexdigest(), len(subjects)


def choose_questions(questions, per_subject, limit, seed, subjects_filter):
    grouped = {}
    for question in questions:
        if subjects_filter and question["subject"] not in subjects_filter:
            continue
        grouped.setdefault(question["subject"], []).append(question)
    missing = subjects_filter - grouped.keys()
    if missing:
        raise ValueError(f"找不到学科：{', '.join(sorted(missing))}")
    rng = random.Random(seed)
    for subject in grouped:
        rng.shuffle(grouped[subject])
        if per_subject:
            grouped[subject] = grouped[subject][:per_subject]
    selected = []
    for index in range(max(map(len, grouped.values()))):
        for subject in sorted(grouped):
            if index < len(grouped[subject]):
                selected.append(grouped[subject][index])
    return selected[:limit] if limit else selected


def make_prompt(question):
    lines = [
        f"以下是中国关于{question['subject_zh']}考试的单项选择题，请选出其中的正确答案。",
        "",
        question["question"],
    ]
    lines += [f"{letter}. {question['options'][letter]}" for letter in "ABCD"]
    lines.append("答案：")
    return "\n".join(lines)


def extract_answer(response):
    text = response.strip().upper().replace("Ａ", "A").replace("Ｂ", "B").replace("Ｃ", "C").replace("Ｄ", "D")
    match = re.fullmatch(r"(?:答案\s*[:：]?\s*|选\s*)?([ABCD])\s*[。.!！]?", text)
    return match.group(1) if match else None


def run(args):
    questions, data_hash, total_subjects = load_questions(args.dataset, args.split)
    selected = choose_questions(questions, args.per_subject, args.limit, args.seed, args.subjects)
    key = get_key()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if args.output.exists():
        for row in read_jsonl(args.output):
            if "error" not in row:
                done.add((row.get("model"), row.get("question_id"), row.get("dataset_sha256"), row.get("prompt_version")))
    print(f"C-Eval {args.split}：{len(questions)} 题、{total_subjects} 学科；本次选 {len(selected)} 题，待运行 {sum((args.model, q['id'], data_hash, PROMPT_VERSION) not in done for q in selected)} 题。", flush=True)
    with args.output.open("a", encoding="utf-8") as output:
        for question in selected:
            slot = (args.model, question["id"], data_hash, PROMPT_VERSION)
            if slot in done:
                continue
            payload = {
                "model": args.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": make_prompt(question)},
                ],
                "max_tokens": args.max_tokens,
                "thinking": {"type": "disabled"},
                "temperature": 0,
                "stream": False,
            }
            record = {
                "time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "benchmark": "C-Eval",
                "split": args.split,
                "dataset_sha256": data_hash,
                "prompt_version": PROMPT_VERSION,
                "model": args.model,
                "thinking": "disabled",
                "temperature": 0,
                "max_tokens": args.max_tokens,
                "question_id": question["id"],
                "subject": question["subject"],
                "subject_zh": question["subject_zh"],
                "category": question["category"],
                "system_prompt": SYSTEM_PROMPT,
                "prompt": payload["messages"][1]["content"],
                "expected": question["answer"],
            }
            start = time.monotonic()
            try:
                response = api_json(args.base_url, "/chat/completions", key, payload, args.timeout)
                record["latency_seconds"] = round(time.monotonic() - start, 3)
                record["response"] = response["choices"][0]["message"].get("content") or ""
                record["extracted"] = extract_answer(record["response"])
                record["correct"] = record["extracted"] == question["answer"]
                record["api_model"] = response.get("model")
                record["finish_reason"] = response["choices"][0].get("finish_reason")
                record["usage"] = response.get("usage", {})
            except (RuntimeError, KeyError, IndexError, TypeError) as exc:
                record["error"] = str(exc)
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()
            print(f"{question['id']}: {'请求失败' if 'error' in record else ('正确' if record['correct'] else '错误')}", flush=True)
            if "error" in record and any(token in record["error"] for token in ("HTTP 401", "HTTP 402", "HTTP 403", "HTTP 404")):
                raise RuntimeError(f"API 返回 {record['error']}，已停止以避免重复请求")


def report(rows):
    if not rows:
        raise ValueError("结果文件为空")
    latest = {}
    for row in rows:
        slot = (row.get("model"), row.get("question_id"), row.get("dataset_sha256"), row.get("prompt_version"))
        latest[slot] = row
    rows = list(latest.values())
    groups = {}
    for row in rows:
        groups.setdefault((row["model"], row["split"], row["dataset_sha256"], row["prompt_version"]), []).append(row)
    lines = ["# C-Eval 评测报告", "", "仅对文件中实际运行的题目计算分数。公开题集可能存在训练数据污染；不同提示、抽题和模型配置的结果不可直接比较。", ""]
    for (model, split, data_hash, prompt_version), group in groups.items():
        valid = [row for row in group if "error" not in row]
        correct = sum(row.get("correct", False) for row in valid)
        subjects = sorted({row["subject"] for row in group})
        per_subject = []
        for subject in subjects:
            subset = [row for row in valid if row["subject"] == subject]
            if subset:
                per_subject.append(sum(row["correct"] for row in subset) / len(subset))
        latencies = [row["latency_seconds"] for row in valid if "latency_seconds" in row]
        lines += [
            f"## {model} · {split}", "",
            f"数据 SHA-256：`{data_hash}`；提示版本：`{prompt_version}`。",
            f"有效回答 {len(valid)}/{len(group)}；请求失败 {len(group)-len(valid)}；无法提取选项 {sum(row.get('extracted') is None for row in valid)}。",
            f"按题目计正确率：{correct}/{len(valid)}（{correct/len(valid):.1%}）。" if valid else "暂无可评分回答。",
            f"按学科等权平均：{statistics.mean(per_subject):.1%}（覆盖 {len(per_subject)} 个学科）。" if per_subject else "暂无学科得分。",
            f"平均请求耗时：{statistics.mean(latencies):.2f} 秒。" if latencies else "无耗时数据。",
            f"输入 token：{sum(row.get('usage', {}).get('prompt_tokens', 0) for row in valid)}；输出 token：{sum(row.get('usage', {}).get('completion_tokens', 0) for row in valid)}。",
            "", "| 类别 | 正确/有效 |", "|---|---:|",
        ]
        for category in sorted({row.get("category", "Unknown") for row in group}):
            subset = [row for row in valid if row.get("category", "Unknown") == category]
            lines.append(f"| {category} | {sum(row.get('correct', False) for row in subset)}/{len(subset)} |")
        lines += ["", "| 学科 | 正确/有效 | 请求失败 |", "|---|---:|---:|"]
        for subject in subjects:
            subset = [row for row in group if row["subject"] == subject]
            ok = [row for row in subset if "error" not in row]
            name = subset[0].get("subject_zh", subject)
            lines.append(f"| {name} (`{subject}`) | {sum(row.get('correct', False) for row in ok)}/{len(ok)} | {len(subset)-len(ok)} |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "run"):
        command = sub.add_parser(name)
        command.add_argument("--dataset", type=Path, required=True, help="官方 ceval-exam.zip 或解压后的目录")
        command.add_argument("--split", choices=("val", "test"), default="val")
        if name == "run":
            command.add_argument("--model", default="deepseek-flash")
            command.add_argument("--base-url", default=DEFAULT_BASE_URL)
            command.add_argument("--output", type=Path, default=ROOT / "results" / "ceval.jsonl")
            command.add_argument("--per-subject", type=int, default=5, help="每学科抽题数；0 表示全部")
            command.add_argument("--limit", type=int, default=0, help="本次请求上限；0 表示全部选中题目")
            command.add_argument("--seed", type=int, default=20261011)
            command.add_argument("--subjects", type=lambda x: set(x.split(",")), default=set())
            command.add_argument("--timeout", type=int, default=120)
            command.add_argument("--max-tokens", type=int, default=32)
    command = sub.add_parser("report")
    command.add_argument("results", type=Path)
    command.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            questions, data_hash, count = load_questions(args.dataset, args.split)
            print(f"C-Eval {args.split}: {len(questions)} 题，{count} 学科，SHA-256 {data_hash}")
        elif args.command == "run":
            if args.per_subject < 0 or args.limit < 0 or args.max_tokens < 1:
                raise ValueError("抽样和输出参数不能为负数")
            run(args)
        else:
            content = report(list(read_jsonl(args.results)))
            if args.markdown:
                args.markdown.parent.mkdir(parents=True, exist_ok=True)
                args.markdown.write_text(content, encoding="utf-8")
                print(f"报告已写入 {args.markdown}")
            else:
                print(content)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
