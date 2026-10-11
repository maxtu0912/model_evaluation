#!/usr/bin/env python3
"""Download the released C-Eval test labels and convert them to local CSVs."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import time
from urllib import request
import zipfile


ROOT = Path(__file__).resolve().parent
MAPPING = ROOT / "cases" / "ceval_subject_mapping.json"
REVISION = "617524a00b307ff6f9933702f724131fe12ca7ce"
FIELDS = ("id", "question", "A", "B", "C", "D", "answer")


def old_rows(archive, subject):
    suffix = f"test/{subject}_test.csv"
    names = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(names) != 1:
        raise ValueError(f"旧数据中找不到唯一的 {subject} 测试集")
    return list(csv.DictReader(io.StringIO(archive.read(names[0]).decode("utf-8-sig"))))


def download(revision, subject):
    url = f"https://huggingface.co/datasets/ceval/ceval-exam/resolve/{revision}/{subject}/test-00000-of-00001.parquet"
    for attempt in range(3):
        try:
            with request.urlopen(url, timeout=60) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default=REVISION)
    parser.add_argument("--old-zip", type=Path, default=ROOT / "data" / "ceval-exam.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "ceval-test-labeled.zip")
    args = parser.parse_args()
    import pyarrow.parquet as parquet

    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"source": "ceval/ceval-exam", "revision": args.revision, "files": {}}
    with zipfile.ZipFile(args.old_zip) as old, zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as new:
        for subject in sorted(mapping):
            content = download(args.revision, subject)
            table = parquet.read_table(io.BytesIO(content))
            if not set(FIELDS).issubset(table.schema.names):
                raise ValueError(f"{subject} 缺少必要字段")
            rows = table.select(FIELDS).to_pylist()
            previous = old_rows(old, subject)
            if len(rows) != len(previous):
                raise ValueError(f"{subject} 题目数与旧数据不一致")
            for current, earlier in zip(rows, previous):
                if any(str(current[field]) != earlier[field] for field in FIELDS[:-1]):
                    raise ValueError(f"{subject} 新旧题目不一致，须人工核对")
                if current["answer"] not in {"A", "B", "C", "D"}:
                    raise ValueError(f"{subject} 存在无效答案")
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            entry = zipfile.ZipInfo(f"ceval-exam/test/{subject}_test.csv", (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            new.writestr(entry, stream.getvalue())
            manifest["files"][subject] = {"rows": len(rows), "parquet_sha256": hashlib.sha256(content).hexdigest()}
            print(f"{subject}: {len(rows)}", flush=True)
    manifest["questions"] = sum(item["rows"] for item in manifest["files"].values())
    manifest["output_sha256"] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"共 {manifest['questions']} 题，输出 {args.output}")


if __name__ == "__main__":
    main()
