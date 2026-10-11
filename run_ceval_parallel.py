#!/usr/bin/env python3
"""Run every C-Eval subject concurrently, with one resumable file per subject."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from types import SimpleNamespace

import ceval


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", choices=("val", "test"), default="test")
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit-per-subject", type=int, default=0)
    parser.add_argument("--parts-dir", type=Path, default=ceval.ROOT / "results" / "ceval-test-parts")
    parser.add_argument("--output", type=Path, default=ceval.ROOT / "results" / "ceval-deepseek-test.jsonl")
    args = parser.parse_args()
    if args.workers < 1 or args.limit_per_subject < 0:
        parser.error("workers 必须大于 0，limit-per-subject 不能为负")

    questions, data_hash, _ = ceval.load_questions(args.dataset, args.split)
    subjects = sorted({question["subject"] for question in questions})
    args.parts_dir.mkdir(parents=True, exist_ok=True)

    def run_subject(subject):
        part = args.parts_dir / f"{subject}.jsonl"
        run_args = SimpleNamespace(
            dataset=args.dataset,
            split=args.split,
            per_subject=0,
            limit=args.limit_per_subject,
            seed=20261011,
            subjects={subject},
            model=args.model,
            output=part,
            base_url=ceval.DEFAULT_BASE_URL,
            max_tokens=32,
            timeout=120,
        )
        ceval.run(run_args)
        return subject

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_subject, subject): subject for subject in subjects}
        for future in as_completed(futures):
            subject = futures[future]
            try:
                future.result()
                print(f"完成学科：{subject}", flush=True)
            except Exception as exc:
                failures.append((subject, str(exc)))
                print(f"学科失败：{subject}: {exc}", flush=True)
    if failures:
        raise RuntimeError(f"{len(failures)} 个学科运行失败，请检查分卷记录后续跑")

    latest = {}
    for subject in subjects:
        for row in ceval.read_jsonl(args.parts_dir / f"{subject}.jsonl"):
            if row.get("model") == args.model and row.get("dataset_sha256") == data_hash and row.get("prompt_version") == ceval.PROMPT_VERSION:
                latest[row["question_id"]] = row
    if args.limit_per_subject:
        selected = [
            question
            for subject in subjects
            for question in ceval.choose_questions(questions, 0, args.limit_per_subject, 20261011, {subject})
        ]
    else:
        selected = ceval.choose_questions(questions, 0, 0, 20261011, set())
    expected_ids = {question["id"] for question in selected}
    bad = [row for row in latest.values() if "error" in row]
    if set(latest) != expected_ids or bad:
        raise RuntimeError(f"结果不完整：已有 {len(latest)}/{len(expected_ids)} 题，API 失败 {len(bad)} 题")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for question in selected:
            stream.write(json.dumps(latest[question["id"]], ensure_ascii=False) + "\n")
    print(f"合并完成：{len(selected)} 题，输出 {args.output}")


if __name__ == "__main__":
    main()
