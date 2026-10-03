"""Portfolio formula, propagation, evidence and hostile AI boundary regression tests."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from dataclasses import replace
from aeroplan.config import Config
from aeroplan.data import generate
from aeroplan.portfolio import (PortfolioConfig, SCENARIOS, masters, indicators, costs, run_portfolio)
from aeroplan.planning import simulate
from aeroplan.insights import select_insights
from aeroplan.validation import validate_inputs, validate_result

class PortfolioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=Config(); cls.base=generate(cls.cfg)
        cls.tmp=tempfile.TemporaryDirectory(); cls.out=Path(cls.tmp.name)
        cls.result=run_portfolio(cls.base,cls.cfg,cls.out)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def test_scenario_master_and_ibp_propagation(self):
        before=copy.deepcopy(self.base)
        digests=[]
        for name in SCENARIOS:
            d,items=masters(self.base,name)
            validate_inputs(d,self.cfg)
            ref=simulate(d,self.cfg); actual=simulate(d,self.cfg,4,ref)
            validate_result(actual,d,self.cfg,ref)
            saved=json.loads((self.out/name.lower().replace(' ','_')/'ibp_result.json').read_text())
            from aeroplan.storage import canonical
            self.assertEqual(canonical(actual),saved)
            digests.append(self.result['audit'][name]['master_digest'])
            # Aircraft demand and physical shipset quantities remain comparable.
            self.assertEqual(d['customer_orders'],before['customer_orders'])
            for p in d['products']:
                self.assertEqual(sum(r['quantity'] for r in d['aircraft_bom'] if r['product']==p['product']),4)
        self.assertEqual(self.base,before)
        self.assertEqual(len(set(digests)),4)
        self.assertEqual(len({a['result_digest'] for a in self.result['audit'].values()}),4)
        rows=self.result['rows']
        self.assertEqual([r['active_items'] for r in rows],[7,5,7,3])
        self.assertGreater(len({r['otif'] for r in rows}),1)
        self.assertGreater(len({r['average_inventory_units'] for r in rows}),1)

    def test_index_formula_and_custom_weights(self):
        d,items=masters(self.base,'Baseline'); r=simulate(d,self.cfg,4)
        policy=PortfolioConfig()
        raw,parts=indicators(d,items,r,self.cfg,policy)
        expected=100*sum(policy.weights[k]*min(1,raw[k]/policy.scales[k]) for k in policy.weights)
        self.assertAlmostEqual(raw['complexity_index'],expected)
        weights=dict.fromkeys(policy.weights,0);weights['active_items']=1
        changed,_=indicators(d,items,r,self.cfg,replace(policy,weights=weights))
        self.assertEqual(changed['complexity_index'],100)
        self.assertAlmostEqual(raw['cross_aircraft_commonality'],1/7)
        self.assertEqual(raw['variants'],4)
        self.assertEqual(raw['order_frequency'],1)
        self.assertAlmostEqual(raw['exception_frequency'],len(r['exceptions'])/(len(r['orders'])*self.cfg.weeks))
        self.assertAlmostEqual(raw['lifecycle_maturity'],(1+2*(.9+.7+.3))/7)

    def test_cost_formula_small_known_ledger(self):
        items=[{'component':'X','unit_value':100,'lifecycle_maturity':.5}]
        data={'suppliers':[{'vendor_group':'V'},{'vendor_group':'V'}]}
        result={'exceptions':[{},{}],'material':[{'component':'X','closing_units':10},{'component':'X','closing_units':20}]}
        p=PortfolioConfig(); c=costs(data,items,result,p,baseline_items=2)
        self.assertEqual(c,dict(item_administration=1200,supplier_administration=2400,
                               exception_handling=70,inventory_holding=6,lifecycle_support=450,conversion=8000))

    def test_cost_reconciliation_and_rank(self):
        for row in self.result['rows']:
            self.assertAlmostEqual(row['cost_of_complexity'],sum(self.result['audit'][row['portfolio_scenario']]['cost_breakdown'].values()))
            self.assertAlmostEqual(row['total_modeled_cost'],row['cost_of_complexity']+row['recovery_cost'])
        self.assertEqual([r['cost_rank'] for r in sorted(self.result['rows'],key=lambda r:r['total_modeled_cost'])],[1,2,3,4])

    def test_reproducibility_all_text_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);run_portfolio(self.base,self.cfg,out)
            files=[p for p in self.out.rglob('*') if p.is_file()]
            self.assertEqual(len(files),len([p for p in out.rglob('*') if p.is_file()]))
            for p in files: self.assertEqual(p.read_bytes(),(out/p.relative_to(self.out)).read_bytes(),str(p))

    def test_evidence_ids_resolve_and_records_match(self):
        package=self.result['package']
        for candidate in package['candidates']:
            for sid in candidate['evidence_ids']: self.assertIn(sid,package['calculated_facts'])
        for row in self.result['rows']:
            self.assertEqual(package['calculated_facts']['portfolio_comparison:'+row['portfolio_scenario']]['record'],row)
        for sid,source in package['calculated_facts'].items():
            if 'json' in source:
                self.assertEqual(json.loads((self.out/source['json']).read_text()),source['record'])
        self.assertEqual(len(select_insights(package)['interpretations']),4)
        broken=copy.deepcopy(package);broken['calculated_facts'].clear()
        with self.assertRaises(ValueError): select_insights(broken)

    def test_ai_cannot_modify_kpis_ranking_or_evidence(self):
        package=copy.deepcopy(self.result['package']);original=copy.deepcopy(package)
        def hostile(p):
            for source in p['calculated_facts'].values(): source['record']['otif']=1;source['record']['cost_rank']=0
            p['candidates'][0]['interpretation']='Fabricated savings'
            return {'selected_ids':[p['candidates'][0]['id']], 'cost_rank':0}
        response=select_insights(package,hostile)
        self.assertEqual(package,original)
        self.assertEqual(response['mode'],'deterministic_fallback')
        with tempfile.TemporaryDirectory() as folder:
            actual=run_portfolio(self.base,self.cfg,Path(folder),hostile)
            self.assertEqual(actual['rows'],self.result['rows'])
            self.assertEqual(actual['package'],self.result['package'])

    def test_fallback_and_valid_selection(self):
        p=self.result['package']
        def offline(_): raise OSError('offline')
        self.assertEqual(select_insights(p,offline)['mode'],'deterministic_fallback')
        for value in ({'selected_ids':['bad']},{'selected_ids':[]},{'selected_ids':[p['candidates'][0]['id']],'kpi':10}):
            self.assertEqual(select_insights(p,lambda _:value)['mode'],'deterministic_fallback')
        selected=select_insights(p,lambda _:{'selected_ids':[x['id'] for x in p['candidates']]})
        self.assertEqual(selected['mode'],'local_llm_selection')
        self.assertEqual(selected['interpretations'],p['candidates'])

    def test_configuration_validation(self):
        for kwargs in ({'weights':{}},{'item_admin_cost':-1},{'holding_rate_per_week':float('nan')},
                       {'scales':dict.fromkeys(PortfolioConfig().scales,0)}):
            with self.assertRaises(ValueError): PortfolioConfig(**kwargs)
        with self.assertRaises(ValueError): masters(self.base,'Unknown')

    def test_seed_and_cost_assumptions(self):
        with tempfile.TemporaryDirectory() as folder:
            different=run_portfolio(generate(Config(seed=101)),Config(seed=101),Path(folder))
            self.assertNotEqual(different['package']['source_digest'],self.result['package']['source_digest'])
            changed=run_portfolio(self.base,self.cfg,Path(folder),policy=PortfolioConfig(item_admin_cost=2400))
            for a,b in zip(self.result['rows'],changed['rows']):
                self.assertEqual(a['otif'],b['otif'])
                self.assertAlmostEqual(b['cost_of_complexity']-a['cost_of_complexity'],1200*a['active_items'])
