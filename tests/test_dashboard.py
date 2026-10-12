import copy
import json
from pathlib import Path
import tempfile
import unittest

import build_dashboard as dashboard


ROOT = Path(__file__).resolve().parents[1]


class DashboardTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'dashboard/sources.json').read_text())

    def test_real_reports_reconcile_and_comparison_groups_are_separate(self):
        catalog = dashboard.build(self.config)
        flash, pro, val = catalog['runs'][:3]
        self.assertEqual((flash['counts']['correct'], pro['counts']['correct']), (10861, 11126))
        self.assertAlmostEqual(pro['metrics']['accuracy'], 11126 / 12342 * 100)
        self.assertEqual(flash['comparison_group'], pro['comparison_group'])
        self.assertNotEqual(flash['comparison_group'], val['comparison_group'])
        self.assertEqual(len(pro['dimensions']), 52)
        self.assertEqual(sum(c['counts']['valid'] for c in pro['categories']), 12342)
        serialized = json.dumps(catalog)
        for forbidden in ('DEEPSEEK_API_KEY', 'system_prompt', 'expected', 'response', 'options'):
            self.assertNotIn(f'"{forbidden}"', serialized)

    def test_generated_catalog_is_current(self):
        actual = json.loads((ROOT / 'dashboard/data/catalog.json').read_text())
        self.assertEqual(actual, dashboard.build(self.config))

    def test_incomplete_runs_keep_progress_and_do_not_mix_with_completed_runs(self):
        catalog=dashboard.build(self.config)
        result=copy.deepcopy(catalog['runs'][0])
        result['status']='incomplete'
        result['counts']['expected_total']=12342
        changed=dashboard.normalize_run(result,self.config['sources'][0],self.config['benchmarks'][0])
        self.assertEqual(changed['status'],'incomplete')
        self.assertEqual(changed['counts']['expected_total'],12342)
        self.assertNotEqual(changed['comparison_group'],catalog['runs'][0]['comparison_group'])

    def test_bad_report_totals_are_rejected(self):
        source = self.config['sources'][0]
        report = (ROOT / source['path']).read_text().replace('10861/12342', '10860/12342')
        mapping = json.loads((ROOT / 'cases/ceval_subject_mapping.json').read_text())
        with self.assertRaisesRegex(ValueError, '学科汇总'):
            dashboard.parse_ceval_report(report, source, mapping)

    def test_future_benchmark_metrics_and_model_count_require_no_ceval_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = {'split': 'heldout', 'dataset_fingerprint': 'custom-dataset-v1',
                      'protocol': {'prompt_version': 'v1', 'shots': 0, 'thinking': 'enabled', 'temperature': 0,
                                   'max_tokens': 100, 'selection': 'sample-id-digest'},
                      'metrics': {'score': 7.5, 'duration': 200}, 'counts': {'total': 10},
                      'categories': [], 'dimensions': [{'id': 'logic', 'name': '逻辑', 'metrics': {'score': 7.5, 'duration': None}}],
                      'system_prompt': 'must not leak', 'api_key': 'must not leak'}
            (root / 'result.json').write_text(json.dumps(result))
            config = {'schema_version': 1, 'benchmarks': [{'id': 'custom', 'name': 'Custom', 'metrics': [
                {'id': 'score', 'name': '得分', 'unit': '分', 'range': [0, 10], 'higher_is_better': True},
                {'id': 'duration', 'name': '耗时', 'unit': 'ms', 'higher_is_better': False}]}], 'sources': []}
            for i in range(3):
                config['sources'].append({'id': f'run-{i}', 'format': 'normalized', 'path': 'result.json',
                                          'benchmark_id': 'custom', 'model': {'id': f'model-{i}', 'name': f'Model {i}'}})
            catalog = dashboard.build(config, root)
            self.assertEqual(len(catalog['models']), 3)
            self.assertEqual(catalog['runs'][0]['metrics']['score'], 7.5)
            self.assertEqual(len({r['comparison_group'] for r in catalog['runs']}), 1)
            self.assertNotIn('must not leak', json.dumps(catalog))

    def test_generation_parameters_sampling_and_data_version_split_comparison_groups(self):
        catalog = dashboard.build(self.config)
        original = catalog['runs'][0]
        source = self.config['sources'][0]
        benchmark = self.config['benchmarks'][0]
        for key, value in [('thinking', 'enabled'), ('max_tokens', 64), ('selection', 'sample-42'), ('temperature', 1), ('shots', 5), ('prompt_version', 'next')]:
            result = copy.deepcopy(original)
            result['protocol'][key] = value
            changed = dashboard.normalize_run(result, source, benchmark)
            self.assertNotEqual(original['comparison_group'], changed['comparison_group'])
        result = copy.deepcopy(original)
        result['dataset_fingerprint'] = 'different'
        self.assertNotEqual(original['comparison_group'], dashboard.normalize_run(result, source, benchmark)['comparison_group'])

    def test_duplicate_ids_nonfinite_metrics_and_unknown_metrics_are_rejected(self):
        result = dashboard.build(self.config)['runs'][0]
        source, benchmark = self.config['sources'][0], self.config['benchmarks'][0]
        for mutation in ('duplicate', 'nan', 'unknown'):
            changed = copy.deepcopy(result)
            if mutation == 'duplicate':
                changed['dimensions'].append(changed['dimensions'][0])
            elif mutation == 'nan':
                changed['metrics']['accuracy'] = float('nan')
            else:
                changed['metrics']['unknown'] = 1
            with self.assertRaises(ValueError):
                dashboard.normalize_run(changed, source, benchmark)


if __name__ == '__main__':
    unittest.main()
