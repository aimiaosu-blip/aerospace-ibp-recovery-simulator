"""Behavioral, conservation, perturbation and SQL reconciliation tests (stdlib only)."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from aeroplan.config import Config, WEIGHTS
from aeroplan.data import generate, disrupted_orders
from aeroplan.planning import simulate
from aeroplan.analysis import metrics, evaluate, root_causes
from aeroplan.validation import validate_inputs, validate_result
from aeroplan.__main__ import run


class PlanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = Config()
        cls.data = generate(cls.cfg)
        cls.ref = simulate(cls.data, cls.cfg)
        cls.results = {s: simulate(cls.data, cls.cfg, s, cls.ref) for s in range(5)}

    def test_generator_reproducible_and_seed_sensitive(self):
        self.assertEqual(self.data, generate(self.cfg))
        self.assertNotEqual(self.data['demand_forecast'], generate(replace(self.cfg, seed=43))['demand_forecast'])

    def test_input_foreign_keys_and_uniqueness(self):
        validate_inputs(self.data, self.cfg)
        broken = copy.deepcopy(self.data)
        broken['customer_orders'].append(broken['customer_orders'][0])
        with self.assertRaises(AssertionError):
            validate_inputs(broken, self.cfg)

    def test_baseline_fully_delivers_without_overload(self):
        validate_result(self.ref, self.data, self.cfg)
        self.assertTrue(all(r['on_time'] for r in self.ref['orders']))
        self.assertEqual(sum(r['overload_hours'] for r in self.ref['capacity']), 0)

    def test_all_recoveries_are_feasible_and_history_is_frozen(self):
        for result in self.results.values():
            validate_result(result, self.data, self.cfg, self.ref)

    def test_fixed_masters_are_not_mutated(self):
        self.assertEqual(self.data, generate(self.cfg))

    def test_integer_demand_uplift_within_rounding_tolerance(self):
        orders = disrupted_orders(self.data, self.cfg)
        base = sum(1 for o in self.data['customer_orders'] if o['product']=='AP-100' and o['due_week']>=10)
        extras = [o for o in orders if o['incremental']]
        self.assertLessEqual(abs(len(extras)-.15*base), .5)
        self.assertTrue(all(o['due_week'] >= 10 and o['known_week'] == 10 for o in extras))

    def test_outage_four_release_weeks_and_propagation(self):
        shipments = self.results[0]['shipments']
        reduced = [r for r in shipments if r['available_capacity'] < r['master_capacity']]
        self.assertEqual({r['release_week'] for r in reduced}, {10,11,12,13})
        self.assertEqual({r['arrival_week'] for r in reduced}, {15,16,17,18})
        self.assertTrue(all(r['available_capacity'] == 12 for r in reduced))

    def test_expedite_changes_time_not_total_supply(self):
        total = lambda sid: sum(r['units'] for r in self.results[sid]['shipments'])
        self.assertEqual(total(0), total(1))
        standard = {(r['supplier'],r['release_week']): r['arrival_week'] for r in self.results[0]['shipments']}
        for r in self.results[1]['shipments']:
            if r['mode']=='express':
                self.assertEqual(r['arrival_week'], standard[r['supplier'],r['release_week']]-1)

    def test_secondary_only_uses_existing_qualified_capacity(self):
        rows = [r for r in self.results[2]['shipments'] if r['supplier']=='S-A2']
        self.assertTrue(rows)
        self.assertTrue(all(r['units']<=4 and r['release_week']>=10 for r in rows))
        self.assertTrue(all(r['supplier']!='S-A2' for r in self.results[0]['shipments']))

    def test_no_disruption_reproduces_reference(self):
        cfg = replace(self.cfg, capacity_loss=0, demand_uplift=0)
        result = simulate(self.data, cfg, 0, self.ref)
        self.assertEqual([r['delivery_week'] for r in result['orders']],
                         [r['delivery_week'] for r in self.ref['orders']])

    def test_total_outage_remains_feasible(self):
        cfg = replace(self.cfg, capacity_loss=1, disruption_duration=10)
        result = simulate(self.data, cfg, 0, self.ref)
        validate_result(result, self.data, cfg, self.ref)
        self.assertGreater(sum(r['late_or_open'] for r in result['orders']), 0)
        self.assertEqual(root_causes(result, self.ref, cfg)['constrained_suppliers'], ['S-A1'])

    def test_capacity_drop_backlogs_instead_of_overbooking(self):
        data = copy.deepcopy(self.data)
        for r in data['production_capacity']:
            if r['week'] >= 10:
                r['fal_capacity_hours'] = 0
        result = simulate(data, self.cfg, 0, self.ref)
        validate_result(result, data, self.cfg, self.ref)
        self.assertTrue(all(r['produced']==0 for r in result['weekly'] if r['week']>=10))

    def test_conservation_check_catches_corruption(self):
        result = copy.deepcopy(self.results[0])
        result['material'][0]['closing_units'] += 1
        with self.assertRaises(AssertionError):
            validate_result(result, self.data, self.cfg)

    def test_root_cause_uses_actual_constraint_events(self):
        root = root_causes(self.results[0], self.ref, self.cfg)
        self.assertEqual(root['bottleneck_component'], 'AIRFRAME')
        self.assertEqual(root['constrained_suppliers'], ['S-A1'])
        self.assertEqual(len(root['at_risk_order_ids']), sum(r['late_or_open'] for r in self.results[0]['orders']))

    def test_otif_uses_all_due_orders_including_open(self):
        result = self.results[0]
        m = metrics(result, self.data, self.cfg, 0)
        self.assertAlmostEqual(m['otif'], sum(o['on_time'] for o in result['orders'])/len(result['orders']))
        self.assertEqual(m['ending_backlog'], sum(o['delivery_week'] is None for o in result['orders']))

    def test_weights_validated_and_cost_can_change_decision(self):
        rows = [metrics(r,self.data,self.cfg,s) for s,r in self.results.items()]
        ranking = evaluate(rows)
        cost = dict.fromkeys(WEIGHTS, 0)
        cost['recovery_cost'] = 1
        self.assertEqual(evaluate(rows,cost)[0]['scenario'],0)
        self.assertTrue(all(0 <= r['weighted_score'] <= 1 for r in ranking))
        with self.assertRaises(ValueError):
            evaluate(rows,dict.fromkeys(WEIGHTS,.5))

    def test_equal_criteria_tie_is_stable(self):
        row = metrics(self.results[0],self.data,self.cfg,0)
        rows = [dict(row,scenario=s) for s in range(5)]
        self.assertEqual(evaluate(rows)[0]['scenario'], 0)
        self.assertTrue(all(abs(r['weighted_score']-1)<1e-9 for r in evaluate(rows)))

    def test_alternative_seeds_keep_feasibility(self):
        for seed in (7, 101):
            cfg = replace(self.cfg, seed=seed)
            data = generate(cfg)
            ref = simulate(data,cfg)
            for scenario in range(5):
                validate_result(simulate(data,cfg,scenario,ref), data,cfg,ref)

    def test_invalid_configuration_rejected(self):
        for kwargs in ({'capacity_loss':1.1},{'weeks':0},{'demand_uplift':-.1}, {'secondary_unit_cost':-1}):
            with self.assertRaises(ValueError):
                Config(**kwargs)


class PipelineTests(unittest.TestCase):
    def test_sql_exports_reconcile_and_rerun_is_reproducible(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            run(out)
            before = json.loads((out/'manifest.json').read_text())
            run(out)
            self.assertEqual(before, json.loads((out/'manifest.json').read_text()))
            with sqlite3.connect(out/'aeroplan.sqlite') as con:
                self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                for sid, otif, wape, backlog in con.execute('SELECT scenario,otif,wape,backlog_unit_weeks FROM scenario_metrics'):
                    sql_otif, sql_backlog = con.execute('SELECT 1.0*SUM(on_time_due)/SUM(demand_units),SUM(backlog) FROM weekly_kpi WHERE scenario=?',(sid,)).fetchone()
                    sql_wape = con.execute('SELECT SUM(absolute_error)/SUM(demand_units) FROM forecast_accuracy WHERE scenario=?',(sid,)).fetchone()[0]
                    self.assertAlmostEqual(otif,sql_otif)
                    self.assertAlmostEqual(wape,sql_wape)
                    self.assertEqual(backlog,sql_backlog)
                self.assertEqual(con.execute('SELECT COUNT(*) FROM supplier_release_load WHERE allocated_units>available_capacity').fetchone()[0],0)
                self.assertEqual(con.execute('SELECT COUNT(*) FROM weekly_kpi').fetchone()[0],6*26)
                self.assertEqual(con.execute("SELECT DISTINCT typeof(magnitude) FROM constraint_exceptions").fetchall(), [('real',)])
                # Last four weeks are pooled by numerator and denominator, independently of SQL windows.
                for sid in range(5):
                    rolled = con.execute('SELECT rolling_4w_otif FROM weekly_kpi WHERE scenario=? AND week=26',(sid,)).fetchone()[0]
                    pooled = con.execute('SELECT 1.0*SUM(on_time_due)/SUM(demand_units) FROM production_plan WHERE scenario=? AND week BETWEEN 23 AND 26',(sid,)).fetchone()[0]
                    self.assertAlmostEqual(rolled,pooled)
            self.assertTrue((out/'index.html').exists())
            self.assertTrue((out/'executive_insights.md').exists())


if __name__ == '__main__':
    unittest.main()
