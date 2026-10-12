#!/usr/bin/env python3
"""Small, dependency-free DeepSeek evaluation runner."""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import statistics
import sys
import time
from urllib import error, request


ROOT = Path(__file__).resolve().parent
DEFAULT_CASES = ROOT / "cases" / "pilot.jsonl"
DEFAULT_BASE_URL = "https://api.deepseek.com"
SYSTEM_PROMPT = "请严格按题目要求作答。只给最终答案，不添加解释、Markdown 或多余文字。"


def read_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc


def load_cases(path):
    cases = list(read_jsonl(path))
    if not cases:
        raise ValueError("题库为空")
    seen = set()
    for case in cases:
        for field in ("id", "dimension", "prompt", "answer", "grader"):
            if field not in case:
                raise ValueError(f"题目缺少 {field}: {case}")
        if case["id"] in seen:
            raise ValueError(f"重复题目 ID: {case['id']}")
        seen.add(case["id"])
        if case["grader"] not in ("exact", "number", "json"):
            raise ValueError(f"不支持的评分器: {case['grader']}")
        if case["grader"] == "json" and not isinstance(case["answer"], (dict, list)):
            raise ValueError(f"JSON 标准答案必须是对象或数组: {case['id']}")
        if case["grader"] == "number":
            float(case["answer"])
    return cases


def normalize_text(value):
    return str(value).strip()


def json_equal(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(
            json_equal(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            json_equal(item, value) for item, value in zip(actual, expected)
        )
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(actual) is type(expected) and actual == expected
    return actual == expected


def score(case, response_text):
    kind = case["grader"]
    if kind == "exact":
        return normalize_text(response_text) == normalize_text(case["answer"])
    if kind == "number":
        value = normalize_text(response_text).replace(",", "")
        try:
            return float(value) == float(case["answer"])
        except ValueError:
            return False
    try:
        return json_equal(json.loads(response_text.strip()), case["answer"])
    except json.JSONDecodeError:
        return False


def api_json(base_url, endpoint, key, payload=None, timeout=120):
    if not base_url.startswith("https://") and not base_url.startswith("http://127.0.0.1:"):
        raise ValueError("API 地址必须使用 HTTPS（本机测试地址除外）")
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        base_url.rstrip("/") + endpoint,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    for attempt in range(6):
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except error.HTTPError as exc:
            if exc.code == 429 and attempt < 5:
                try:
                    retry_after = float(exc.headers.get("Retry-After", "0")) if exc.headers else 0
                except ValueError:
                    retry_after = 0
                exc.close()
                time.sleep(min(60, max(2 ** (attempt + 1), retry_after)))
                continue
            # API error bodies can contain account details; keep only the status code.
            raise RuntimeError(f"HTTP {exc.code} from API") from exc
        except error.URLError as exc:
            raise RuntimeError(f"API connection failed: {exc.reason}") from exc


def get_key():
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        env_file = ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("DEEPSEEK_API_KEY="):
                    key = line.partition("=")[2].strip().strip("\"'")
                    break
    if not key:
        raise ValueError("缺少 DEEPSEEK_API_KEY；请在本机终端设置环境变量，或在项目 .env 文件中填写")
    return key


def command_models(args):
    data = api_json(args.base_url, "/models", get_key(), timeout=args.timeout)
    for model in data.get("data", []):
        print(f"{model.get('id', '?')}\t{model.get('name', '')}")


def command_run(args):
    cases = load_cases(args.cases)
    key = get_key()
    if args.limit:
        cases = cases[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    effort = args.reasoning_effort if args.thinking == "enabled" else None
    done = set()
    if args.output.exists():
        for row in read_jsonl(args.output):
            if "error" not in row:
                done.add((row.get("model"), row.get("case_id"), row.get("repeat"), row.get("thinking"), row.get("reasoning_effort")))
    total = len(cases) * args.repeat
    pending = total - sum((args.model, case["id"], rep, args.thinking, effort) in done for case in cases for rep in range(1, args.repeat + 1))
    print(f"模型 {args.model}；共 {total} 次，待运行 {pending} 次；结果写入 {args.output}")
    with args.output.open("a", encoding="utf-8") as stream:
        for case in cases:
            for rep in range(1, args.repeat + 1):
                if (args.model, case["id"], rep, args.thinking, effort) in done:
                    continue
                payload = {
                    "model": args.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": case["prompt"]},
                    ],
                    "stream": False,
                    "max_tokens": args.max_tokens,
                }
                if args.thinking == "enabled":
                    payload["thinking"] = {"type": "enabled"}
                    payload["reasoning_effort"] = args.reasoning_effort
                start = time.monotonic()
                row = {
                    "time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "case_id": case["id"],
                    "dimension": case["dimension"],
                    "model": args.model,
                    "repeat": rep,
                    "thinking": args.thinking,
                    "reasoning_effort": effort,
                    "prompt": case["prompt"],
                    "expected": case["answer"],
                    "grader": case["grader"],
                }
                for attempt in range(3):
                    try:
                        result = api_json(args.base_url, "/chat/completions", key, payload, args.timeout)
                        row["latency_seconds"] = round(time.monotonic() - start, 3)
                        row["response"] = result["choices"][0]["message"].get("content") or ""
                        row["finish_reason"] = result["choices"][0].get("finish_reason")
                        row["usage"] = result.get("usage", {})
                        row["api_model"] = result.get("model")
                        row["correct"] = score(case, row["response"])
                        break
                    except (RuntimeError, KeyError, IndexError, TypeError) as exc:
                        row["error"] = str(exc)
                        if attempt < 2 and ("HTTP 429" in str(exc) or "HTTP 5" in str(exc)):
                            time.sleep(2 ** attempt)
                            continue
                        break
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                status = "错误" if "error" in row else ("正确" if row["correct"] else "未命中")
                print(f"{case['id']} #{rep}: {status}")


def make_report(rows):
    if not rows:
        raise ValueError("结果文件为空")
    # A successful rerun replaces a previous failed attempt for the same slot.
    latest = {}
    for row in rows:
        slot = (row.get("model"), row.get("case_id"), row.get("repeat"), row.get("thinking"), row.get("reasoning_effort"))
        latest[slot] = row
    rows = list(latest.values())
    groups = {}
    for row in rows:
        key = (row.get("model"), row.get("thinking"), row.get("reasoning_effort"))
        groups.setdefault(key, []).append(row)
    lines = ["# DeepSeek 试运行报告", "", "注意：试题数量少且均为可客观判分的文本题，结果不代表全面能力。", ""]
    for (model, thinking, effort), group in groups.items():
        lines += [f"## {model} · thinking={thinking} · effort={effort}", ""]
        valid = [r for r in group if "error" not in r]
        errors = len(group) - len(valid)
        latencies = [r["latency_seconds"] for r in valid if "latency_seconds" in r]
        usage = [r.get("usage", {}) for r in valid]
        lines += [
            f"完成 {len(valid)}/{len(group)} 次请求；请求错误 {errors} 次。",
            f"客观题正确 {sum(bool(r.get('correct')) for r in valid)}/{len(valid)}。" if valid else "暂无可评分回答。",
            f"平均耗时 {statistics.mean(latencies):.2f} 秒。" if latencies else "无耗时数据。",
            f"输入 token {sum(u.get('prompt_tokens', 0) for u in usage)}；输出 token {sum(u.get('completion_tokens', 0) for u in usage)}。",
            "",
            "| 维度 | 正确/有效回答 | 请求错误 |",
            "|---|---:|---:|",
        ]
        for dimension in sorted({r["dimension"] for r in group}):
            subset = [r for r in group if r["dimension"] == dimension]
            ok = [r for r in subset if "error" not in r]
            lines.append(f"| {dimension} | {sum(bool(r.get('correct')) for r in ok)}/{len(ok)} | {len(subset)-len(ok)} |")
        lines += ["", "### 未命中与错误", ""]
        failures = [r for r in group if "error" in r or r.get("correct") is False]
        if failures:
            for row in failures:
                answer = str(row.get("response", row.get("error", ""))).replace("\n", " ")[:160]
                lines.append(f"- `{row['case_id']}` #{row['repeat']}: {answer}")
        else:
            lines.append("无。")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="校验题库")
    validate.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    models = sub.add_parser("models", help="列出账户可用模型")
    models.add_argument("--base-url", default=DEFAULT_BASE_URL)
    models.add_argument("--timeout", type=int, default=30)
    run = sub.add_parser("run", help="运行评测")
    run.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    run.add_argument("--model", default="deepseek-flash")
    run.add_argument("--base-url", default=DEFAULT_BASE_URL)
    run.add_argument("--output", type=Path, default=ROOT / "results" / "pilot.jsonl")
    run.add_argument("--limit", type=int, default=0)
    run.add_argument("--repeat", type=int, default=1)
    run.add_argument("--timeout", type=int, default=120)
    run.add_argument("--max-tokens", type=int, default=256)
    run.add_argument("--thinking", choices=("disabled", "enabled"), default="disabled")
    run.add_argument("--reasoning-effort", choices=("low", "high", "max"), default="high")
    report = sub.add_parser("report", help="生成 Markdown 报告")
    report.add_argument("results", type=Path)
    report.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            print(f"题库有效：{len(load_cases(args.cases))} 题")
        elif args.command == "models":
            command_models(args)
        elif args.command == "run":
            if args.limit < 0 or args.repeat < 1 or args.max_tokens < 1:
                raise ValueError("limit、repeat、max-tokens 参数无效")
            command_run(args)
        else:
            output = make_report(list(read_jsonl(args.results)))
            if args.markdown:
                args.markdown.parent.mkdir(parents=True, exist_ok=True)
                args.markdown.write_text(output, encoding="utf-8")
                print(f"报告已写入 {args.markdown}")
            else:
                print(output)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
