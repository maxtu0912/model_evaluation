import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import mmlu_pro as mmlu


def fixture():
    demo={'question_id':100,'category':'math','question':'demo','options':['one','two'],'answer':'A','answer_index':0,'cot_content':'A: Work it out. The answer is (A).'}
    target={'question_id':1,'category':'math','question':'test','options':['one','two'],'answer':'B','answer_index':1,'cot_content':'NEVER_INCLUDE_TEST_SOLUTION'}
    data={'revision':'test-revision','file_sha256':{},'test':[target], 'validation':[dict(demo,question_id=100+i) for i in range(5)]}
    data['dataset_sha256']=mmlu.digest(data)
    return data


class MMLUProTest(unittest.TestCase):
    def test_prompt_uses_exactly_five_demos_and_never_test_solution(self):
        data=fixture(); prompt=mmlu.make_prompt(data['test'][0],data)
        self.assertEqual(prompt.count('Question: demo'),5)
        self.assertEqual(prompt.count('Question: test'),1)
        self.assertNotIn('NEVER_INCLUDE_TEST_SOLUTION',prompt)
        self.assertTrue(prompt.endswith("Answer: Let's think step by step.\n\n"))

    def test_extraction_does_not_guess_from_reasoning_or_accept_out_of_range(self):
        cases=[('The answer is (B).','B'),('The answer is (A). Correction: The answer is (B).','B'),
               ('**The answer is (b)**','B'),('Answer: B','B'),(' B ','B'),
               ('Compare A and B, then consider C.',None),('The answer is a complex issue.',None),
               ('The answer is (J).',None),('The answer is (AB).',None)]
        for text,expected in cases:
            self.assertEqual(mmlu.extract_answer(text,2),expected,text)

    def test_sampling_is_reproducible_and_pilot_subset_is_reused_in_full(self):
        data=fixture(); data['test']=[dict(data['test'][0],question_id=i) for i in range(20)]
        a=mmlu.choose_questions(data,10,42); b=mmlu.choose_questions(data,0,42)
        self.assertEqual(a,b[:10]); self.assertEqual(a,mmlu.choose_questions(data,10,42))

    def test_resume_checks_exact_request_configuration_and_report_reconciles(self):
        data=fixture()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); dataset=root/'dataset.json'; dataset.write_text(json.dumps(data))
            args=SimpleNamespace(dataset=dataset,model='deepseek-flash',service_name='Flash test',max_tokens=4000,
                                 per_category=0,seed=42,workers=1,output=root/'rows.jsonl',base_url='https://api.deepseek.com',timeout=1)
            def fake(*_):
                return {'model':'deepseek-flash','choices':[{'message':{'content':'The answer is (B).'},'finish_reason':'stop'}], 'usage':{'prompt_tokens':10,'completion_tokens':5}}
            with patch.object(mmlu,'get_key',return_value='fake'),patch.object(mmlu,'api_json',side_effect=fake) as api:
                mmlu.run(args); mmlu.run(args); self.assertEqual(api.call_count,1)
                args.max_tokens=5000; mmlu.run(args); self.assertEqual(api.call_count,2)
            report_args=SimpleNamespace(**vars(args),aggregate=root/'aggregate.json',markdown=root/'report.md',require_complete=True)
            result=mmlu.aggregate(report_args)
            self.assertEqual(result['counts']['correct'],1); self.assertEqual(result['metrics']['accuracy'],100)
            self.assertEqual(result['protocol']['selection'],'full')
            row=json.loads(args.output.read_text().splitlines()[-1]); row['correct']=False
            args.output.write_text(json.dumps(row)+'\n')
            with self.assertRaisesRegex(ValueError,'逐题记录'):
                mmlu.aggregate(report_args)

    def test_dataset_fingerprint_detects_changes(self):
        data=fixture(); data['test'][0]['answer']='A'
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'dataset.json'; p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'指纹'):
                mmlu.load_dataset(p)


if __name__=='__main__':
    unittest.main()
