"""Run `python -m aeroplan --output artifacts` from the repository root."""
import argparse
from dataclasses import asdict, replace
from pathlib import Path
from .config import Config, SCENARIOS
from .data import generate
from .planning import simulate
from .analysis import metrics, evaluate, root_causes, sensitivity
from .validation import validate_inputs, validate_result
from .storage import store_tables, write_json, manifest
from .reporting import report


def run(output=Path('artifacts'), seed=42):
    """Execute generation -> finite planning -> validation -> SQL -> decision reporting."""
    cfg = Config(seed=seed)
    data = generate(cfg)
    validate_inputs(data, cfg)
    reference = simulate(data, cfg)
    results = {-1: reference}
    validations = {-1: validate_result(reference, data, cfg)}
    for scenario in range(5):
        results[scenario] = simulate(data, cfg, scenario, reference)
        validations[scenario] = validate_result(results[scenario], data, cfg, reference)
    metric_rows = [metrics(result, data, cfg, sid) for sid, result in results.items()]
    ranking = evaluate(metric_rows)
    root = root_causes(results[0], reference, cfg)
    profiles = sensitivity(metric_rows)
    root['counterfactuals'] = []
    for label, cf in [('demand_only', replace(cfg, capacity_loss=0)),
                      ('capacity_only', replace(cfg, demand_uplift=0))]:
        cf_result = simulate(data, cf, 0, reference)
        validate_result(cf_result, data, cf, reference)
        root['counterfactuals'].append(dict(case=label, **metrics(cf_result, data, cf, 0)))
    root['first_receipt_deficit_week'] = min((r['week'] for r in root['receipt_deficits']), default=None)
    tables = dict(data)
    names = {'weekly': 'production_plan', 'material': 'material_balance', 'shipments': 'supply_shipments',
             'orders': 'order_fulfillment', 'capacity': 'capacity_execution', 'exceptions': 'planning_exceptions'}
    for key, name in names.items():
        tables[name] = [row for result in results.values() for row in result[key]]
    tables['scenario_metrics'] = metric_rows
    tables['scenario_evaluation'] = sorted(ranking, key=lambda r:r['scenario'])
    tables['dim_scenario'] = [{'scenario': sid, 'scenario_name': name} for sid, name in SCENARIOS.items()]
    tables['dim_week'] = [{'week': w, 'week_label': f'W{w:02d}',
                          'phase': 'Pre-event' if w < cfg.disruption_week else 'Post-event'} for w in range(1, cfg.weeks+1)]
    first_release = min(r['release_week'] for r in tables['supply_shipments'])
    tables['dim_release_week'] = [{'release_week': w, 'release_week_label': f'W{w:02d}'}
                                  for w in range(first_release, cfg.weeks+1)]
    out = Path(output)
    store_tables(out, tables, Path(__file__).resolve().parents[1]/'sql'/'analytics.sql')
    write_json(out/'root_causes.json', root)
    write_json(out/'validation.json', validations)
    write_json(out/'sensitivity.json', profiles)
    manifest(out, asdict(cfg))
    report(out, metric_rows, ranking, root, profiles, cfg)
    return {'output': str(out), 'recommended_scenario': ranking[0]['scenario'], 'validation': 'passed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('artifacts'))
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    print(run(args.output, args.seed))


if __name__ == '__main__':
    main()
