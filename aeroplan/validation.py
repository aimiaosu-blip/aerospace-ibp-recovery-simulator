"""Fail loudly on infeasible supply, assembly, material flow or time travel."""
from collections import defaultdict


def validate_inputs(data, cfg):
    """Validate foreign keys, positive quantities and unique business keys."""
    for table, keys in [('products', ('product',)), ('components', ('component',)),
                        ('suppliers', ('supplier',)), ('customer_orders', ('order_id',)),
                        ('aircraft_bom', ('product', 'component')),
                        ('production_capacity', ('week',)), ('inventory', ('component',)),
                        ('transportation', ('supplier',)),
                        ('demand_forecast', ('vintage_week', 'week', 'product'))]:
        values = [tuple(r[k] for k in keys) for r in data[table]]
        assert len(values) == len(set(values)), f'Duplicate key in {table}'
    products = {r['product'] for r in data['products']}
    components = {r['component'] for r in data['components']}
    for r in data['aircraft_bom']:
        assert r['product'] in products and r['component'] in components and r['quantity'] > 0
    for r in data['customer_orders']:
        assert r['product'] in products and r['quantity'] == 1 and 1 <= r['due_week'] <= cfg.weeks
    for r in data['suppliers']:
        assert r['component'] in components and r['weekly_capacity'] >= 0 and r['qualified'] == 1
        assert r['manufacturing_weeks'] >= 0
    assert len(data['production_capacity']) == cfg.weeks
    assert all(r['opening_units'] >= 0 for r in data['inventory'])


def validate_result(result, data, cfg, reference=None):
    """Check conservation, allocation limits, unique fulfillment, and frozen history."""
    allocated, express = defaultdict(int), defaultdict(int)
    capacities, limits = {}, {r['supplier']: r['express_capacity'] for r in data['transportation']}
    for r in result['shipments']:
        key = r['supplier'], r['release_week']
        allocated[key] += r['units']
        capacities[key] = r['available_capacity']
        assert r['units'] >= 0 and r['available_capacity'] <= r['master_capacity']
        assert r['arrival_week'] == r['release_week'] + r['manufacturing_weeks'] + r['transit_weeks']
        if r['mode'] == 'express':
            express[key] += r['units']
            assert r['release_week'] >= cfg.disruption_week
    assert all(units <= capacities[key] for key, units in allocated.items()), 'Supplier overload'
    assert all(units <= limits[key[0]] for key, units in express.items()), 'Express overload'
    ledger_receipts, actual_consumed = defaultdict(int), defaultdict(int)
    for shipment in result['shipments']:
        ledger_receipts[shipment['arrival_week'], shipment['component']] += shipment['units']
    bom = {(r['product'], r['component']): r['quantity'] for r in data['aircraft_bom']}
    product_hours = {r['product']: r['fal_hours'] for r in data['products']}
    completion_hours = defaultdict(float)
    for order in result['orders']:
        if order['delivery_week'] is not None:
            completion_hours[order['delivery_week']] += product_hours[order['product']]
            for c in {r['component'] for r in data['components']}:
                actual_consumed[order['delivery_week'], c] += bom[order['product'], c]
    last_stock = {r['component']: r['opening_units'] for r in data['inventory']}
    for r in result['material']:
        key = r['week'], r['component']
        assert r['receipts'] == ledger_receipts[key], 'Receipt ledger mismatch'
        assert r['consumed'] == actual_consumed[key], 'BOM consumption mismatch'
        assert r['opening_units'] == last_stock[r['component']], 'Inventory continuity mismatch'
        last_stock[r['component']] = r['closing_units']
        assert r['closing_units'] == r['opening_units'] + r['receipts'] - r['consumed']
        assert min(r['opening_units'], r['closing_units'], r['consumed']) >= 0, 'Negative inventory'
    assert all(abs(r['used_hours']-completion_hours[r['week']]) < 1e-9 for r in result['capacity'])
    assert all(0 <= r['used_hours'] <= r['available_hours'] + 1e-9 for r in result['capacity'])
    ids = [r['order_id'] for r in result['orders']]
    assert len(ids) == len(set(ids)), 'Duplicate delivery'
    assert sum(r['delivery_week'] is not None for r in result['orders']) == sum(r['produced'] for r in result['weekly'])
    for r in result['orders']:
        assert r['delivery_week'] is None or r['known_week'] <= r['delivery_week'] <= cfg.weeks
    due, produced = defaultdict(int), defaultdict(int)
    for r in result['weekly']:
        due[r['product']] += r['demand_units']
        produced[r['product']] += r['produced']
        # Early completions require tracking future-due deliveries separately.
        early = sum(1 for o in result['orders'] if o['product'] == r['product'] and o['due_week'] > r['week']
                    and o['delivery_week'] is not None and o['delivery_week'] <= r['week'])
        assert r['backlog'] == due[r['product']] - produced[r['product']] + early
    if reference:
        def frozen(rows):
            return [{k: v for k, v in r.items() if k != 'scenario'} for r in rows if r['week'] < cfg.disruption_week]
        # Coverage is forward looking and intentionally excludes unannounced extra orders.
        for key in ('weekly', 'material', 'capacity'):
            assert frozen(result[key]) == frozen(reference[key]), f'History changed in {key}'
    return {'status': 'passed', 'checks': ['supplier_capacity', 'transport_capacity', 'lead_times',
            'inventory_conservation', 'nonnegative_inventory', 'fal_capacity', 'unique_fulfillment',
            'backlog_conservation', 'order_knowledge', 'frozen_history']}
