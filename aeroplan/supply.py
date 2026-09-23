"""Finite source allocations and lead-time-aware receipts, with a fixed opening pipeline."""
from collections import defaultdict


def plan_supply(data, orders, cfg, scenario):
    """Respect immutable capacities; primary loss is an availability event, not a master edit.

    Release quantities use vintage-1 consensus demand. Secondary allocation can recover
    lost volume and absorb new demand from week 10; it never raises source capacity.
    Express applies only to new releases from week 10, never retroactively to receipts.
    """
    routes = {x['supplier']: x for x in data['transportation']}
    bom = {(x['product'], x['component']): x['quantity'] for x in data['aircraft_bom']}
    demand = defaultdict(int)
    for o in data['customer_orders']:
        demand[o['due_week'], o['product']] += o['quantity']
    forecast = {(x['week'], x['product']): x['forecast_units']
                for x in data['demand_forecast'] if x['vintage_week'] == 1}
    requirements = defaultdict(int)
    for (week, product), units in demand.items():
        consensus = max(units, int(forecast[week, product] + .5))
        for component in [x['component'] for x in data['components']]:
            requirements[week, component] += consensus * bom[product, component]
    increments = defaultdict(int)
    for o in orders:
        if o['incremental']:
            increments[o['due_week']] += 1
    suppliers = {x['supplier']: x for x in data['suppliers']}
    rows, receipts = [], defaultdict(int)

    def append(s, release, units, available, planned, express=False):
        route = routes[s['supplier']]
        fast = min(units, route['express_capacity']) if express else 0
        for mode, qty, transit in [('express', fast, route['express_weeks']),
                                    ('standard', units-fast, route['standard_weeks'])]:
            # Retain a zero-volume standard row for a fully unavailable source;
            # its capacity event must remain observable in root-cause analytics.
            if qty == 0 and not (units == 0 and mode == 'standard'):
                continue
            arrival = release + s['manufacturing_weeks'] + transit
            row = {'scenario': scenario, 'supplier': s['supplier'], 'component': s['component'],
                   'release_week': release, 'arrival_week': arrival, 'mode': mode, 'units': qty,
                   'master_capacity': s['weekly_capacity'], 'available_capacity': available,
                   'planned_primary_units': planned, 'manufacturing_weeks': s['manufacturing_weeks'],
                   'transit_weeks': transit, 'opening_pipeline': int(release < 1),
                   'incremental_cost': qty * ((cfg.expedite_unit_cost if mode == 'express' else 0)
                                             + (cfg.secondary_unit_cost if s['secondary'] else 0))}
            rows.append(row)
            receipts[arrival, s['component']] += qty

    for s in data['suppliers']:
        if s['secondary']:
            continue
        lead = s['manufacturing_weeks'] + routes[s['supplier']]['standard_weeks']
        for release in range(1-lead, cfg.weeks-lead+1):
            due = release + lead
            planned = requirements[due, s['component']]
            active_loss = (scenario >= 0 and s['supplier'] == 'S-A1'
                           and cfg.disruption_week <= release < cfg.disruption_week + cfg.disruption_duration)
            available = int(s['weekly_capacity'] * (1-cfg.capacity_loss)) if active_loss else s['weekly_capacity']
            primary = min(planned, available)
            expedite = scenario in (1, 4) and release >= cfg.disruption_week and s['component'] == 'AIRFRAME'
            append(s, release, primary, available, planned, expedite)
            if scenario in (2, 4) and s['component'] == 'AIRFRAME' and release >= cfg.disruption_week:
                second = suppliers['S-A2']
                secondary = min(second['weekly_capacity'], planned-primary + increments[due])
                append(second, release, secondary, second['weekly_capacity'], 0, scenario == 4)
    return rows, receipts
