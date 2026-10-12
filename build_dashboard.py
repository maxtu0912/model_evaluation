#!/usr/bin/env python3
"""Build a public aggregate-only dashboard catalog from registered result sources."""

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parent


def parse_ceval_report(text, source, mapping):
    # Read only the first benchmark block, before any comparison appendix.
    block = text.split("## 与仓库", 1)[0]
    model, split = re.search(r"^## (\S+) · (\S+)$", block, re.M).groups()
    if model != source["model"]["id"]:
        raise ValueError("报告模型与注册模型不一致")
    fingerprint, prompt = re.search(r"数据 SHA-256：`([^`]+)`；提示版本：`([^`]+)`", block).groups()
    valid, total, failed, unparsed = map(int, re.search(r"有效回答 (\d+)/(\d+)；请求失败 (\d+)；无法提取选项 (\d+)", block).groups())
    correct, denominator = map(int, re.search(r"按题目计正确率：(\d+)/(\d+)", block).groups())
    if valid != denominator or valid + failed != total or unparsed > valid:
        raise ValueError("报告请求数与评分分母不一致")
    dimensions = []
    categories = defaultdict(list)
    for match in re.finditer(r"^\| ([^|]+?) \(`([^`]+)`\) \| (\d+)/(\d+) \| (\d+) \|$", block, re.M):
        name, subject, c, n, errors = match.groups()
        c, n, errors = int(c), int(n), int(errors)
        if not 0 <= c <= n or n <= 0:
            raise ValueError("学科计数不合法")
        category = mapping[subject]["category"]
        item = {"id": subject, "name": name.strip(), "category_id": category,
                "counts": {"correct": c, "valid": n, "total": n + errors, "failed": errors},
                "metrics": {"accuracy": c / n * 100, "macro_accuracy": c / n * 100}}
        dimensions.append(item)
        categories[category].append(item)
    if not dimensions or sum(d["counts"]["valid"] for d in dimensions) != valid or sum(d["counts"]["correct"] for d in dimensions) != correct:
        raise ValueError("学科汇总与报告总分不一致")
    names = {"STEM": "理工科", "Humanities": "人文学科", "Social Science": "社会科学", "Other": "其他 / 职业资格等"}
    category_rows = []
    for category, items in categories.items():
        c = sum(x["counts"]["correct"] for x in items)
        n = sum(x["counts"]["valid"] for x in items)
        check = re.search(rf"^\| {re.escape(category)} \| (\d+)/(\d+) \|$", block, re.M)
        if not check or tuple(map(int, check.groups())) != (c, n):
            raise ValueError("类别汇总与报告不一致")
        category_rows.append({"id": category, "name": names.get(category, category),
                              "counts": {"correct": c, "valid": n},
                              "metrics": {"accuracy": c / n * 100, "macro_accuracy": statistics.mean(x["metrics"]["accuracy"] for x in items)}})
    latency = float(re.search(r"平均请求耗时：([\d.]+) 秒", block)[1])
    inputs, outputs = map(int, re.search(r"输入 token：(\d+)；输出 token：(\d+)", block).groups())
    return {"split": split, "dataset_fingerprint": fingerprint,
            "protocol": {**source["protocol"], "prompt_version": prompt},
            "counts": {"total": total, "valid": valid, "correct": correct, "failed": failed, "unparsed": unparsed},
            "metrics": {"accuracy": correct / valid * 100, "macro_accuracy": statistics.mean(x["metrics"]["accuracy"] for x in dimensions)},
            "categories": category_rows, "dimensions": dimensions,
            "operational": {"latency_seconds": latency, "input_tokens": inputs, "output_tokens": outputs, "latency_comparable": False}}


def finite_metrics(metrics):
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError("metrics 必须包含至少一个指标")
    for value in metrics.values():
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError("指标必须为有限数字或 null")


def normalize_run(result, source, benchmark):
    required = ("split", "dataset_fingerprint", "protocol", "metrics", "categories", "dimensions")
    if any(key not in result for key in required):
        raise ValueError("归一化结果缺少必要字段")
    protocol_keys = ("prompt_version", "shots", "thinking", "temperature", "max_tokens", "selection")
    if any(key not in result["protocol"] for key in protocol_keys):
        raise ValueError("protocol 缺少比较配置字段")
    if not result["dataset_fingerprint"] or not result["protocol"]["selection"]:
        raise ValueError("数据指纹和抽样标识不能为空")
    metric_ids = {m["id"] for m in benchmark["metrics"]}
    finite_metrics(result["metrics"])
    if set(result["metrics"]) - metric_ids:
        raise ValueError("存在未在评测集注册的指标")
    # Explicit allowlist: prompts, answers, credentials and arbitrary metadata never enter the catalog.
    clean = {"id": source["id"], "benchmark_id": source["benchmark_id"], "model_id": source["model"]["id"],
             "date": source.get("date"), "source": source["path"], "notes": source.get("notes", []),
             "split": result["split"], "dataset_fingerprint": result["dataset_fingerprint"],
             "protocol": {k: result["protocol"][k] for k in protocol_keys}, "metrics": result["metrics"]}
    clean["status"] = result.get("status", "completed")
    if clean["status"] not in ("completed", "incomplete"):
        raise ValueError("运行状态必须为 completed 或 incomplete")
    count_keys = ("total", "valid", "correct", "failed", "unparsed", "expected_total")
    def counts(value):
        output = {k: value[k] for k in count_keys if k in value}
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in output.values()):
            raise ValueError("计数字段必须为非负整数")
        if "correct" in output and "valid" in output and output["correct"] > output["valid"]:
            raise ValueError("正确数不能超过有效数")
        return output
    clean["counts"] = counts(result.get("counts", {}))
    for kind in ("categories", "dimensions"):
        clean[kind] = []
        ids = set()
        for item in result[kind]:
            if item["id"] in ids:
                raise ValueError(f"{kind} 中 ID 重复")
            ids.add(item["id"])
            finite_metrics(item["metrics"])
            if set(item["metrics"]) - metric_ids:
                raise ValueError("明细存在未注册指标")
            row = {"id": item["id"], "name": item["name"], "metrics": item["metrics"], "counts": counts(item.get("counts", {}))}
            if kind == "dimensions":
                row["category_id"] = item.get("category_id")
            clean[kind].append(row)
    category_ids = {c["id"] for c in clean["categories"]}
    if any(d["category_id"] is not None and d["category_id"] not in category_ids for d in clean["dimensions"]):
        raise ValueError("明细引用了未注册类别")
    if "operational" in result:
        keys = ("latency_seconds", "input_tokens", "output_tokens", "latency_comparable")
        clean["operational"] = {k: result["operational"][k] for k in keys if k in result["operational"]}
    signature = {k: clean[k] for k in ("benchmark_id", "split", "dataset_fingerprint", "protocol", "status")}
    clean["comparison_group"] = hashlib.sha256(json.dumps(signature, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    return clean


def build(config, root=ROOT):
    if config.get("schema_version") != 1:
        raise ValueError("不支持的数据版本")
    benchmarks = {b["id"]: b for b in config["benchmarks"]}
    if len(benchmarks) != len(config["benchmarks"]):
        raise ValueError("评测集 ID 重复")
    for b in benchmarks.values():
        metrics = b["metrics"]
        if not metrics or len({m["id"] for m in metrics}) != len(metrics):
            raise ValueError("指标注册为空或 ID 重复")
        for m in metrics:
            if not isinstance(m.get("higher_is_better"), bool):
                raise ValueError("指标必须声明比较方向")
            if "range" in m and (len(m["range"]) != 2 or not m["range"][0] < m["range"][1]):
                raise ValueError("指标范围不合法")
    runs, models, seen = [], {}, set()
    mapping = None
    for source in config["sources"]:
        if source["id"] in seen:
            raise ValueError("运行 ID 重复")
        seen.add(source["id"])
        if source["benchmark_id"] not in benchmarks:
            raise ValueError("评测集未注册")
        path = (root / source["path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("来源必须位于仓库内")
        if source["format"] == "ceval-report":
            if mapping is None:
                mapping = json.loads((root / "cases/ceval_subject_mapping.json").read_text())
            result = parse_ceval_report(path.read_text(), source, mapping)
        elif source["format"] == "normalized":
            result = json.loads(path.read_text())
        else:
            raise ValueError("未知来源格式")
        model = {k: source["model"][k] for k in ("id", "name", "provider") if k in source["model"]}
        if model["id"] in models and models[model["id"]] != model:
            raise ValueError("同一模型 ID 的名称或提供方不一致")
        models[model["id"]] = model
        runs.append(normalize_run(result, source, benchmarks[source["benchmark_id"]]))
    return {"schema_version": 1, "benchmarks": list(benchmarks.values()), "models": list(models.values()), "runs": runs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "dashboard/sources.json")
    parser.add_argument("--output", type=Path, default=ROOT / "dashboard/data/catalog.json")
    args = parser.parse_args()
    catalog = build(json.loads(args.config.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    print(f"已导出 {len(catalog['models'])} 个模型、{len(catalog['benchmarks'])} 个评测集、{len(catalog['runs'])} 次运行 → {args.output}")


if __name__ == "__main__":
    main()
