#!/usr/bin/env python3
"""Resumable, bounded Ark text-to-image smoke evaluation (no automatic quality score)."""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import time
from urllib import request, error

ROOT = Path(__file__).resolve().parent
MODEL = 'doubao-seedream-5-0-flash-260915'
ENDPOINT = 'https://ark.cn-beijing.volces.com/api/v3/images/generations'

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def get_key():
    if os.getenv('ARK_API_KEY'):
        return os.environ['ARK_API_KEY']
    for line in (ROOT / '.env').read_text().splitlines():
        if line.startswith('ARK_API_KEY='):
            return line.partition('=')[2].strip().strip('"\'')
    raise ValueError('缺少 ARK_API_KEY')

def generate(payload, key):
    req = request.Request(ENDPOINT, data=json.dumps(payload, ensure_ascii=False).encode(),
                          headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with request.urlopen(req, timeout=180) as response:
            return json.load(response)
    except error.HTTPError as exc:
        # Never log account-specific response bodies, authorization or signed URLs.
        try:
            code = json.load(exc).get('error', {}).get('code', '')
        except (ValueError, AttributeError):
            code = ''
        safe_code = code if code in ('ModelNotOpen', 'AuthenticationError', 'InvalidParameter') else ''
        raise RuntimeError(f'HTTP {exc.code}' + (f' {safe_code}' if safe_code else '')) from None
    except (error.URLError, TimeoutError):
        raise RuntimeError('网络异常或超时；生成状态未知，不自动重试') from None

def run(args):
    cases = [json.loads(line) for line in args.cases.read_text().splitlines() if line.strip()]
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('题目 ID 重复')
    cases = cases[:args.limit]
    args.output.mkdir(parents=True, exist_ok=True)
    log = args.output / 'records.jsonl'
    previous = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    latest = {row['request_fingerprint']: row for row in previous}
    attempted = {fingerprint for fingerprint, row in latest.items()
                 if not (args.retry_rejected and row.get('error') in ('HTTP 404', 'HTTP 404 ModelNotOpen'))}
    key = get_key()
    for case in cases:
        payload = {'model': args.model, 'prompt': case['prompt'], 'size': '1024x1024',
                   'response_format': 'b64_json', 'output_format': 'png', 'watermark': False}
        fingerprint = digest({'endpoint': ENDPOINT, 'payload': payload, 'case': case})
        if fingerprint in attempted:
            print(case['id'] + ': 已尝试，跳过（失败也不自动重试）', flush=True)
            continue
        row = {'id': case['id'], 'category': case['category'], 'prompt': case['prompt'],
               'checks': case['checks'], 'request': payload, 'request_fingerprint': fingerprint,
               'dataset_fingerprint': digest(cases), 'started_at': dt.datetime.now(dt.timezone.utc).isoformat(),
               'quality_status': 'pending_review'}
        start = time.monotonic()
        # Persist an intent before the billable POST; interrupted runs will not duplicate requests.
        row['status'] = 'unknown'
        with log.open('a') as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        try:
            response = generate(payload, key)
            data = response.get('data', [])
            if len(data) != 1 or not data[0].get('b64_json'):
                raise RuntimeError('响应未包含唯一一张 Base64 图片')
            content = base64.b64decode(data[0]['b64_json'], validate=True)
            if not content.startswith(b'\x89PNG\r\n\x1a\n'):
                raise RuntimeError('响应不是 PNG 图片')
            path = args.output / (case['id'] + '.png')
            path.write_bytes(content)
            row.update(status='success', artifact=path.name, sha256=hashlib.sha256(content).hexdigest(),
                       actual_size=data[0].get('size'), response_model=response.get('model'),
                       usage=response.get('usage', {}))
        except Exception as exc:
            row.update(status='failed_or_unknown', error=str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__)
        row['latency_seconds'] = round(time.monotonic() - start, 3)
        with log.open('a') as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        print(f"{case['id']}: {row['status']} ({row['latency_seconds']}s)", flush=True)
        if row['status'] != 'success':
            print('停止新增请求，请先检查失败原因；不切换模型。', flush=True)
            break

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default=MODEL)
    parser.add_argument('--cases', type=Path, default=ROOT / 'cases/image-smoke-v1.jsonl')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/seedream-flash-smoke')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--retry-rejected', action='store_true', help='仅重试此前被 HTTP 404 拒绝的请求')
    args = parser.parse_args()
    if not 1 <= args.limit <= 10:
        parser.error('本轮最多 10 次生成')
    run(args)
