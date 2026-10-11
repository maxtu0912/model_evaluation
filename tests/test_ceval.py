import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import ceval


CSV = "id,question,A,B,C,D,answer,explanation\n0,2+2等于多少？,2,3,4,5,C,\n"


class CEvalTest(unittest.TestCase):
    def make_data(self, directory):
        path = Path(directory) / "ceval-exam.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("ceval-exam/val/computer_network_val.csv", CSV)
            archive.writestr("ceval-exam/val/operating_system_val.csv", CSV)
        return path

    def test_load_select_and_extract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_data(directory)
            questions, digest, count = ceval.load_questions(path, "val")
            self.assertEqual((len(questions), count), (2, 2))
            self.assertEqual(len(digest), 64)
            self.assertIn("计算机网络", ceval.make_prompt(questions[0]))
            self.assertEqual(len(ceval.choose_questions(questions, 1, 1, 123, set())), 1)
            self.assertEqual(ceval.extract_answer("答案：C。"), "C")
            self.assertIsNone(ceval.extract_answer("A 或 C"))

    def test_run_resume_and_report(self):
        calls = []

        def fake_api(base_url, endpoint, key, payload, timeout):
            calls.append(payload)
            self.assertEqual(endpoint, "/chat/completions")
            self.assertEqual([message["role"] for message in payload["messages"]], ["system", "user"])
            return {"model": "fake", "choices": [{"message": {"content": "C"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 1}}

        with tempfile.TemporaryDirectory() as directory:
            data = self.make_data(directory)
            output = Path(directory) / "results.jsonl"
            args = SimpleNamespace(dataset=data, split="val", per_subject=1, limit=2, seed=7, subjects=set(), model="deepseek-flash", output=output, base_url="https://api.deepseek.com", max_tokens=32, timeout=30)
            with patch.object(ceval, "get_key", return_value="fake"), patch.object(ceval, "api_json", fake_api):
                ceval.run(args)
                ceval.run(args)
            self.assertEqual(len(calls), 2)
            rows = list(ceval.read_jsonl(output))
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row["correct"] for row in rows))
            self.assertIn("100.0%", ceval.report(rows))


if __name__ == "__main__":
    unittest.main()
