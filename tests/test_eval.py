import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import eval as evaluator


class EvaluationTest(unittest.TestCase):
    def test_rate_limit_recovers_without_changing_request(self):
        limited = evaluator.error.HTTPError("https://api.deepseek.com/chat/completions", 429, "limited", {"Retry-After": "3"}, io.BytesIO(b"private error"))
        response = io.BytesIO(b'{"model":"deepseek-v4-pro"}')
        payload = {"model": "deepseek-v4-pro", "thinking": {"type": "disabled"}, "temperature": 0}
        with patch.object(evaluator.request, "urlopen", side_effect=[limited, response]) as call, patch.object(evaluator.time, "sleep") as sleep:
            result = evaluator.api_json(evaluator.DEFAULT_BASE_URL, "/chat/completions", "fake-key", payload)
        self.assertEqual(result["model"], "deepseek-v4-pro")
        self.assertEqual(call.call_args_list[0].args[0].data, call.call_args_list[1].args[0].data)
        self.assertEqual(json.loads(call.call_args.args[0].data), payload)
        sleep.assert_called_once_with(3)

    def test_persistent_rate_limit_is_bounded_and_auth_error_is_not_retried(self):
        for status, expected_calls in ((429, 6), (401, 1)):
            with self.subTest(status=status):
                failure = evaluator.error.HTTPError("https://api.deepseek.com", status, "private account detail", {}, None)
                with patch.object(evaluator.request, "urlopen", side_effect=failure) as call, patch.object(evaluator.time, "sleep"):
                    with self.assertRaisesRegex(RuntimeError, f"^HTTP {status} from API$"):
                        evaluator.api_json(evaluator.DEFAULT_BASE_URL, "/models", "fake-key")
                self.assertEqual(call.call_count, expected_calls)

    def test_scoring(self):
        self.assertTrue(evaluator.score({"grader": "number", "answer": 198}, "198"))
        self.assertFalse(evaluator.score({"grader": "number", "answer": 198}, "约 198 元"))
        self.assertTrue(evaluator.score({"grader": "json", "answer": {"a": 1}}, '{"a":1}'))
        self.assertFalse(evaluator.score({"grader": "json", "answer": {"a": 1}}, "```json\n{\"a\":1}\n```"))

    def test_run_resume_and_report(self):
        calls = []

        def fake_api(base_url, endpoint, key, payload, timeout):
            calls.append(payload)
            self.assertEqual(endpoint, "/chat/completions")
            self.assertEqual(payload["model"], "deepseek-flash")
            return {
                "model": "fake-snapshot",
                "choices": [{"message": {"content": "B"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 1},
            }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            args = SimpleNamespace(
                cases=ROOT / "cases" / "pilot.jsonl", model="deepseek-flash",
                limit=1, repeat=1, output=path, base_url="https://api.deepseek.com",
                timeout=30, max_tokens=256, thinking="disabled", reasoning_effort="high",
            )
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "fake-test-key"}), patch.object(evaluator, "api_json", fake_api):
                evaluator.command_run(args)
                evaluator.command_run(args)
            self.assertEqual(len(calls), 1)
            rows = list(evaluator.read_jsonl(path))
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]["correct"])
            self.assertIn("中文理解", evaluator.make_report(rows))


if __name__ == "__main__":
    unittest.main()
