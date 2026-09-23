"""Deterministic finite greedy scheduler; a heuristic, not a mathematical optimizer."""
from collections import defaultdict
from .data import disrupted_orders
from .supply import plan_supply


def simulate(data, cfg, scenario=-1, reference=None):
    """Roll the execution clock weekly, preserving inventory, unfinished orders and history.

    Orders are indivisible one-aircraft commitments. Assembly is one weekly bucket;
    completion and delivery coincide. Replanning can prebuild known orders by two weeks.
    """
    orders = ([dict(o) for o in data['customer_orders']] if scenario == -1
              else disrupted_orders(data, cfg))
    shipments, receipts = plan_supply(data, orders, cfg, scenario)
    stock = {x['component']: x['opening_units'] for x in data['inventory']}
    hours = {x['product']: x['fal_hours'] for x in data['products']}
    bom = defaultdict(dict)
    for row in data['aircraft_bom']:
        bom[row['product']][row['component']] = row['quantity']
    capacity = {x['week']: x['fal_capacity_hours'] for x in data['production_capacity']}
    ref = {(r['week'], r['product']): r['produced'] for r in reference['weekly']} if reference else {}
    completed, weekly, material, exceptions, snapshots = {}, [], [], [], []
    for week in range(1, cfg.weeks+1):
        opening = stock.copy()
        for c in stock:
            stock[c] += receipts[week, c]
        consumed = defaultdict(int)
        used, produced = 0.0, defaultdict(int)
        reschedule = scenario in (3, 4) and week >= cfg.disruption_week
        lookahead = cfg.lookahead if reschedule else 0
        known_pending = [o for o in orders if o['known_week'] <= week and o['order_id'] not in completed]
        # Diagnostic load is due/backlog demand before finite scheduling, never booked overload.
        due_pending = [o for o in known_pending if o['due_week'] <= week]
        load = sum(hours[o['product']] for o in due_pending)
        candidates = [o for o in known_pending if o['due_week'] <= week + lookahead]
        if reschedule:
            candidates.sort(key=lambda o: (o['due_week'] > week, o['priority'], o['due_week'], o['order_id']))
        else:
            candidates.sort(key=lambda o: (o['due_week'], o['order_id']))
        blocked = defaultdict(int)
        for o in candidates:
            product = o['product']
            missing = [c for c, qty in bom[product].items() if stock[c] < qty]
            if missing and o['due_week'] <= week:
                for c in missing:
                    blocked[c] += 1
                    exceptions.append({'scenario': scenario, 'week': week, 'order_id': o['order_id'],
                                       'product': product, 'constraint_type': 'material', 'resource': c})
            if used + hours[product] > capacity[week] + 1e-9:
                if o['due_week'] <= week:
                    exceptions.append({'scenario': scenario, 'week': week, 'order_id': o['order_id'],
                                       'product': product, 'constraint_type': 'capacity', 'resource': 'FAL'})
                continue
            if missing:
                continue
            for c, qty in bom[product].items():
                stock[c] -= qty
                consumed[c] += qty
            used += hours[product]
            produced[product] += 1
            completed[o['order_id']] = week
        for c in stock:
            next_weeks = range(week+1, min(cfg.weeks, week+4)+1)
            future = sum(bom[o['product']][c] for o in orders
                         if o['known_week'] <= week and o['due_week'] in next_weeks)
            denominator = min(4, cfg.weeks-week)
            avg = future / denominator if denominator else 0
            material.append({'scenario': scenario, 'week': week, 'component': c,
                             'opening_units': opening[c], 'receipts': receipts[week, c],
                             'consumed': consumed[c], 'closing_units': stock[c],
                             'coverage_weeks': stock[c]/avg if avg else None,
                             'stockout': int(stock[c] == 0), 'blocked_orders': blocked[c]})
        for product in hours:
            due = [o for o in orders if o['product'] == product and o['due_week'] == week]
            backlog = sum(1 for o in orders if o['product'] == product and o['due_week'] <= week
                          and o['order_id'] not in completed)
            planned = ref.get((week, product), produced[product])
            weekly.append({'scenario': scenario, 'week': week, 'product': product,
                           'demand_units': len(due), 'produced': produced[product], 'baseline_plan': planned,
                           'absolute_deviation': abs(produced[product]-planned), 'backlog': backlog,
                           'on_time_due': sum(completed.get(o['order_id'], cfg.weeks+1) <= week for o in due),
                           'used_hours': produced[product]*hours[product]})
        snapshots.append({'scenario': scenario, 'week': week, 'available_hours': capacity[week],
                          'used_hours': used, 'unconstrained_load_hours': load,
                          'overload_hours': max(0, load-capacity[week]),
                          'known_open_orders': len(known_pending),
                          'rescheduling_enabled': int(reschedule)})
    deliveries = []
    for o in orders:
        delivery = completed.get(o['order_id'])
        deliveries.append(dict(o, scenario=scenario, delivery_week=delivery,
                               on_time=int(delivery is not None and delivery <= o['due_week']),
                               late_or_open=int(delivery is None or delivery > o['due_week']),
                               delay_weeks=(delivery if delivery is not None else cfg.weeks)-o['due_week']
                               if delivery is None or delivery > o['due_week'] else 0))
    return {'weekly': weekly, 'material': material, 'shipments': shipments, 'orders': deliveries,
            'exceptions': exceptions, 'capacity': snapshots}
