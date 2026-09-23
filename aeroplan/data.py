"""Seeded fictional master data and demand. No network or company datasets."""
import random
from .config import Config


def generate(cfg: Config):
    """Create masters, unit orders and weekly forecast vintages deterministically."""
    rng = random.Random(cfg.seed)
    products = [
        {'product': 'AP-100', 'description': 'Narrow-body single-aisle', 'fal_hours': 1.0},
        {'product': 'AP-200', 'description': 'Medium-body', 'fal_hours': 1.5},
        {'product': 'AP-300', 'description': 'Wide-body long-range', 'fal_hours': 2.0},
    ]
    components = [{'component': c, 'description': d} for c, d in [
        ('AIRFRAME', 'Long-lead airframe shipset'), ('ENGINE', 'Engine unit'),
        ('AVIONICS', 'Avionics shipset')]]
    suppliers = [
        {'supplier': 'S-A1', 'component': 'AIRFRAME', 'weekly_capacity': 20, 'manufacturing_weeks': 3, 'secondary': 0, 'qualified': 1},
        {'supplier': 'S-A2', 'component': 'AIRFRAME', 'weekly_capacity': 4, 'manufacturing_weeks': 3, 'secondary': 1, 'qualified': 1},
        {'supplier': 'S-E1', 'component': 'ENGINE', 'weekly_capacity': 44, 'manufacturing_weeks': 4, 'secondary': 0, 'qualified': 1},
        {'supplier': 'S-V1', 'component': 'AVIONICS', 'weekly_capacity': 22, 'manufacturing_weeks': 2, 'secondary': 0, 'qualified': 1},
    ]
    transport = [{'supplier': s['supplier'], 'standard_weeks': 2 if s['component'] == 'AIRFRAME' else 1,
                  'express_weeks': 1, 'express_capacity': 12 if s['component'] == 'AIRFRAME' else 0}
                 for s in suppliers]
    bom = [{'product': p['product'], 'component': c['component'],
            'quantity': 2 if c['component'] == 'ENGINE' else 1} for p in products for c in components]
    inventory = [{'component': c['component'], 'opening_units': 4 if c['component'] != 'ENGINE' else 8,
                  'target_coverage_weeks': .5} for c in components]
    orders, forecasts, capacities = [], [], []
    for week in range(1, cfg.weeks + 1):
        capacities.append({'week': week, 'fal_capacity_hours': 22.0 if week <= 13 else 25.0})
        for p, base in zip(products, (10, 4, 2)):
            qty = base + (2 if p['product'] == 'AP-100' and week > 13 else 0)
            for _ in range(qty):
                orders.append({'order_id': f'O{len(orders)+1:05d}', 'product': p['product'],
                               'due_week': week, 'quantity': 1, 'priority': rng.choice([1, 2, 2, 3]),
                               'known_week': 1, 'incremental': 0})
            # Vintages only use a fixed synthetic signal plus forecast noise, not execution outcomes.
            for vintage in range(1, week + 1):
                forecasts.append({'vintage_week': vintage, 'week': week, 'product': p['product'],
                                  'forecast_units': round(max(0, qty * (1 + rng.uniform(-.08, .08))), 3)})
    return {'products': products, 'components': components, 'suppliers': suppliers,
            'aircraft_bom': bom, 'inventory': inventory, 'transportation': transport,
            'customer_orders': orders, 'demand_forecast': forecasts, 'production_capacity': capacities}


def disrupted_orders(data, cfg):
    """Add integer aircraft by cumulative rounding; uplift within half a unit of 15%."""
    orders = [dict(o) for o in data['customer_orders']]
    cumulative, previous = 0, 0
    for week in range(cfg.disruption_week, cfg.weeks + 1):
        cumulative += sum(o['quantity'] for o in data['customer_orders']
                          if o['product'] == 'AP-100' and o['due_week'] == week)
        target = int(cumulative * cfg.demand_uplift + .5)
        for n in range(target - previous):
            orders.append({'order_id': f'X{week:02d}-{n+1:02d}', 'product': 'AP-100',
                           'due_week': week, 'quantity': 1, 'priority': 1,
                           'known_week': cfg.disruption_week, 'incremental': 1})
        previous = target
    return orders
