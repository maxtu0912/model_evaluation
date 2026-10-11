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
