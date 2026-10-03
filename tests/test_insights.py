"""Evidence integrity, adversarial adapter behavior and pipeline isolation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from aeroplan.__main__ import run
from aeroplan.insights import build_package, select_insights, ollama_selector


class InsightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        run(cls.out)
        cls.package = json.loads((cls.out/'exception_evidence.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fallback_covers_all_five_kinds_and_is_reproducible(self):
        result = select_insights(self.package)
        self.assertEqual(result, select_insights(self.package))
        self.assertEqual(result['mode'], 'deterministic_fallback')
        self.assertEqual({r['kind'] for r in result['interpretations']},
                         {'demand_capacity', 'material_shortage', 'inventory_backlog',
                          'supply_risk', 'recovery_tradeoff'})

    def test_every_reference_resolves_to_exact_sql_record(self):
        import sqlite3
        with sqlite3.connect(self.out/'aeroplan.sqlite') as con:
            con.row_factory = sqlite3.Row
            for source in self.package['calculated_facts'].values():
                key = source['key']
                where = ' AND '.join(f'"{k}"=?' for k in key)
                rows = con.execute(f'SELECT * FROM "{source["table"]}" WHERE {where}',
                                   list(key.values())).fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(dict(rows[0]), source['record'])
        for candidate in self.package['candidates']:
            self.assertTrue(candidate['evidence_ids'])
            self.assertTrue(all(s in self.package['calculated_facts'] for s in candidate['evidence_ids']))

    def test_missing_reference_fails_closed(self):
        package = copy.deepcopy(self.package)
        del package['calculated_facts'][package['candidates'][0]['evidence_ids'][0]]
        with self.assertRaises(ValueError):
            select_insights(package)

    def test_valid_model_can_select_but_not_rewrite(self):
        ids = [r['id'] for r in select_insights(self.package)['interpretations']]
        result = select_insights(self.package, lambda p: {'selected_ids': ids[::-1]})
        self.assertEqual(result['mode'], 'local_llm_selection')
        lookup = {r['id']: r for r in self.package['candidates']}
        self.assertEqual(result['interpretations'], [lookup[i] for i in ids[::-1]])

    def test_invalid_model_responses_fall_back(self):
        ids = [r['id'] for r in select_insights(self.package)['interpretations']]
        for response in (None, [], {'selected_ids': []}, {'selected_ids': ['invented']},
                         {'selected_ids': ids + ids}, {'selected_ids': [ids[0]]},
                         {'selected_ids': [12]}, {'selected_ids': ids, 'otif': 1.0},
                         {'selected_ids': ids, 'interpretation': 'Guaranteed savings'}):
            with self.subTest(response=response):
                result = select_insights(self.package, lambda p: response)
                self.assertEqual(result['mode'], 'deterministic_fallback')

    def test_mutating_adapter_cannot_change_package_or_kpis(self):
        before = copy.deepcopy(self.package)
        def corrupt(package):
            package['calculated_facts'].clear()
            package['candidates'][0]['interpretation'] = 'Invented savings'
            return {'selected_ids': ['invented']}
        select_insights(self.package, corrupt)
        self.assertEqual(self.package, before)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            run(out, selector=corrupt)
            self.assertEqual((out/'manifest.json').read_bytes(), (self.out/'manifest.json').read_bytes())
            self.assertEqual((out/'exception_evidence.json').read_bytes(),
                             (self.out/'exception_evidence.json').read_bytes())

    def test_offline_ollama_failure_falls_back(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=OSError('offline')):
            result = select_insights(self.package, ollama_selector('test-model'))
        self.assertEqual(result['mode'], 'deterministic_fallback')
        self.assertIn('OSError', result['fallback_reason'])

    def test_ollama_request_and_response_contract(self):
        ids = [r['id'] for r in select_insights(self.package)['interpretations']]
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {'response': json.dumps({'selected_ids': ids})}).encode()
        with patch('urllib.request.OpenerDirector.open', return_value=response) as opened:
            result = select_insights(self.package, ollama_selector('test-model'))
        self.assertEqual(result['mode'], 'local_llm_selection')
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/generate')
        self.assertEqual(json.loads(request.data)['model'], 'test-model')

    def test_empty_candidate_set_is_honest(self):
        package = dict(self.package, candidates=[], calculated_facts={})
        self.assertEqual(select_insights(package)['interpretations'], [])

    def test_alternative_seed_changes_evidence_but_not_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            run(out, seed=101)
            package = json.loads((out/'exception_evidence.json').read_text())
            self.assertNotEqual(package['source_digest'], self.package['source_digest'])
            self.assertTrue(select_insights(package)['interpretations'])

    def test_package_builder_does_not_mutate_inputs(self):
        import sqlite3
        from aeroplan.insights import KEYS
        with sqlite3.connect(self.out/'aeroplan.sqlite') as con:
            con.row_factory = sqlite3.Row
            tables = {table: [dict(r) for r in con.execute('SELECT * FROM '+table)] for table in KEYS}
        before = copy.deepcopy(tables)
        build_package(tables)
        self.assertEqual(before, tables)
