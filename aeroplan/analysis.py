"""Auditable KPIs, evidence-based constraint diagnosis and multi-criteria evaluation."""
from collections import Counter, defaultdict
from statistics import pstdev
from .config import WEIGHTS


def metrics(result, data, cfg, scenario):
    """Compute ratios from numerators/denominators, never averages of percentages."""
    weekly, orders = result['weekly'], result['orders']
    coverage = [r['coverage_weeks'] for r in result['material'] if r['coverage_weeks'] is not None]
    # Stability penalizes both variability and deviation from the fixed target coverage.
    targets = {r['component']: r['target_coverage_weeks'] for r in data['inventory']}
    target_error = sum(abs(r['coverage_weeks']-targets[r['component']]) for r in result['material']
                       if r['coverage_weeks'] is not None) / len(coverage) if coverage else 0
    instability = (pstdev(coverage) if coverage else 0) + target_error
    planned = sum(r['baseline_plan'] for r in weekly)
    forecast = {(r['week'], r['product']): r['forecast_units'] for r in data['demand_forecast']
                if r['vintage_week'] == 1}
    demand = sum(r['demand_units'] for r in weekly)
    error = sum(abs(r['demand_units']-forecast[r['week'], r['product']]) for r in weekly)
    changed_units = sum(r['absolute_deviation'] for r in weekly if r['week'] >= cfg.disruption_week) / 2
    action_cost = sum(r['incremental_cost'] for r in result['shipments'])
    reschedule_cost = changed_units * cfg.resequence_unit_cost if scenario in (3, 4) else 0
    released = sum(r['units'] for r in result['shipments'] if r['release_week'] >= cfg.disruption_week
                   and r['component'] == 'AIRFRAME')
    expedited = sum(r['units'] for r in result['shipments'] if r['mode'] == 'express')
    secondary = sum(r['units'] for r in result['shipments'] if r['supplier'] == 'S-A2')
    late = sum(r['late_or_open'] for r in orders) / len(orders) if orders else 0
    # Transparent proxy, not a calibrated probability; delivery risk plus execution complexity.
    risk = min(1.0, .50*late + .25*expedited/max(1, released)
               + .15*secondary/max(1, released)
               + .10*min(1, changed_units/max(1, planned)))
    return {'scenario': scenario, 'demand_units': demand, 'produced': sum(r['produced'] for r in weekly),
            'otif': sum(r['on_time'] for r in orders)/len(orders) if orders else 0,
            'ending_backlog': sum(r['backlog'] for r in weekly if r['week'] == cfg.weeks),
            'backlog_unit_weeks': sum(r['backlog'] for r in weekly),
            'capacity_utilization': sum(r['used_hours'] for r in result['capacity']) /
                                    sum(r['available_hours'] for r in result['capacity']),
            'plan_adherence': max(0, 1-sum(r['absolute_deviation'] for r in weekly)/max(1, planned)),
            'wape': error/max(1, demand), 'inventory_instability': instability,
            'inventory_stability': 1/(1+instability),
            'recovery_cost': action_cost+reschedule_cost, 'operational_risk': risk,
            'stockout_component_weeks': sum(r['stockout'] for r in result['material']),
            'overload_weeks': sum(r['overload_hours'] > 0 for r in result['capacity'])}


def evaluate(metrics_rows, weights=None):
    """Min-max utility within scenarios 0–4. Ties prefer lower cost then lower ID.

    Equal criteria get utility 1. Backlog reduction uses unit-weeks (not just the
    ending snapshot). Zero baseline backlog yields a neutral reduction of zero.
    """
    weights = WEIGHTS if weights is None else weights
    if set(weights) != set(WEIGHTS) or any(w < 0 for w in weights.values()) or abs(sum(weights.values())-1) > 1e-9:
        raise ValueError('Weights must be nonnegative, contain all five criteria, and sum to one')
    rows = [dict(r) for r in metrics_rows if r['scenario'] >= 0]
    baseline = next(r['backlog_unit_weeks'] for r in rows if r['scenario'] == 0)
    for r in rows:
        r['backlog_reduction'] = (baseline-r['backlog_unit_weeks'])/baseline if baseline else 0.0
        r['weighted_score'] = 0.0
    for criterion, weight in weights.items():
        lo, hi = min(r[criterion] for r in rows), max(r[criterion] for r in rows)
        for r in rows:
            utility = (r[criterion]-lo)/(hi-lo) if hi != lo else 1.0
            if criterion in ('recovery_cost', 'operational_risk') and hi != lo:
                utility = 1-utility
            r[criterion+'_utility'] = utility
            r['weighted_score'] += weight*utility
    rows.sort(key=lambda r: (-r['weighted_score'], r['recovery_cost'], r['scenario']))
    for rank, r in enumerate(rows, 1):
        r['rank'] = rank
    return rows


def root_causes(result, reference, cfg):
    """Trace loss -> receipt timing -> blocking events -> orders, without claiming causal uniqueness."""
    material_counts = Counter(r['resource'] for r in result['exceptions'] if r['constraint_type'] == 'material')
    bottleneck = material_counts.most_common(1)[0][0] if material_counts else None
    # Split transport rows must not double-count release capacity or planned quantity.
    releases = {}
    for r in result['shipments']:
        releases[r['supplier'], r['release_week']] = r
    constrained = sorted({r['supplier'] for r in releases.values() if r['available_capacity'] < r['master_capacity']})
    impacted = Counter(r['product'] for r in result['orders'] if r['late_or_open'])
    ref_receipts, actual_receipts = defaultdict(int), defaultdict(int)
    for r in reference['shipments']:
        ref_receipts[r['arrival_week'], r['component']] += r['units']
    for r in result['shipments']:
        actual_receipts[r['arrival_week'], r['component']] += r['units']
    receipt_deficits = [{'week': w, 'component': c, 'missing_vs_reference': units-actual_receipts[w, c]}
                        for (w, c), units in sorted(ref_receipts.items())
                        if 1 <= w <= cfg.weeks and actual_receipts[w, c] < units]
    return {'bottleneck_component': bottleneck, 'material_block_events': dict(material_counts),
            'constrained_suppliers': constrained,
            'most_affected_family': impacted.most_common(1)[0][0] if impacted else None,
            'late_or_open_orders_by_family': dict(impacted),
            'at_risk_order_ids': [r['order_id'] for r in result['orders'] if r['late_or_open']],
            'stockout_weeks': sorted({r['week'] for r in result['material'] if r['stockout']}),
            'capacity_overload_weeks': [r['week'] for r in result['capacity'] if r['overload_hours'] > 0],
            'receipt_deficits': receipt_deficits,
            'first_material_block_week': min((r['week'] for r in result['exceptions']
                                              if r['constraint_type'] == 'material'), default=None),
            'interpretation': 'Constraint attribution from the simulated event ledger; material and FAL constraints can co-occur. At-risk includes already late and horizon-open orders.'}


def sensitivity(rows):
    """Re-rank with three explicit stakeholder preferences, not outcome-tuned weights."""
    profiles = {'balanced': WEIGHTS,
                'service_first': dict(zip(WEIGHTS, (.45, .30, .10, .05, .10))),
                'cost_cautious': dict(zip(WEIGHTS, (.20, .15, .10, .40, .15)))}
    return [{'profile': name, 'winner': evaluate(rows, weights)[0]['scenario'], 'weights': weights}
            for name, weights in profiles.items()]
