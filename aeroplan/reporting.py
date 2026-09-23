"""Generate an executive memo and self-contained visual summary from calculated results."""
from html import escape
from .config import SCENARIOS


def report(out, metrics_rows, ranking, root, profiles, cfg):
    winner = ranking[0]
    by_id = {r['scenario']: r for r in metrics_rows}
    drift = by_id[0]
    lines = ['# Executive decision brief', '',
             '> Entirely synthetic AeroPlan Manufacturing simulation. No Airbus data, affiliation or SAP implementation.', '',
             f"Recommend **Scenario {winner['scenario']}: {SCENARIOS[winner['scenario']]}** under the balanced weights.",
             f"Its weighted score is {winner['weighted_score']:.3f}; OTIF is {winner['otif']:.1%}, versus {drift['otif']:.1%} with no action.",
             f"Backlog exposure falls by {winner['backlog_reduction']:.1%}; incremental recovery cost is {winner['recovery_cost']:,.0f} fictional USD.", '',
             '## Decision table', '', '|Scenario|OTIF|End backlog|Backlog unit-weeks|Cost (USD)|Risk proxy|Score|',
             '|---|---:|---:|---:|---:|---:|---:|']
    for r in sorted(ranking, key=lambda r:r['scenario']):
        lines.append(f"|{r['scenario']} — {SCENARIOS[r['scenario']]}|{r['otif']:.1%}|{r['ending_backlog']}|{r['backlog_unit_weeks']}|{r['recovery_cost']:,.0f}|{r['operational_risk']:.3f}|{r['weighted_score']:.3f}|")
    lines += ['', '## Diagnosis and action', '',
              f"First supplier-driven receipt deficit is in Week {root['first_receipt_deficit_week']}; earlier blocking can reflect demand pressure and opening buffers.",
              f"The event ledger identifies **{root['bottleneck_component']}** as the largest material blocker and **{', '.join(root['constrained_suppliers']) or 'none'}** as the capacity-reduced source.",
              f"The largest late/open order count is in **{root['most_affected_family']}**. First material blocking occurs in Week {root['first_material_block_week']}.",
              f"Demand exceeds available FAL hours in {len(root['capacity_overload_weeks'])} weeks under Scenario 0; the executed plan never exceeds FAL capacity.",
              f"There are {len(root['at_risk_order_ids'])} late or horizon-open orders in Scenario 0. Inspect `root_causes.json` and `csv/order_risk.csv` for traceable IDs.", '',
              '## Sensitivity and governance', '']
    for cf in root['counterfactuals']:
        lines.append(f"- Counterfactual {cf['case']}: OTIF {cf['otif']:.1%}, backlog exposure {cf['backlog_unit_weeks']} aircraft-weeks. These effects need not add linearly.")
    for p in profiles:
        lines.append(f"- {p['profile']}: Scenario {p['winner']} ranks first.")
    lines += ['', 'Authorize only the selected planning levers within existing master-data limits. Review the order-risk queue weekly, monitor airframe receipt timing, and revisit weights with the decision owner.',
              'Costs and operational risk are illustrative policy inputs, not supplier quotes or calibrated failure probabilities. Min-max scores depend on the alternatives included.',
              'Ending backlog excludes orders after the horizon; late/open order delay is censored at the horizon. Forecast accuracy compares vintage 1 against synthetic orders, not real customer consumption.', '']
    (out/'executive_insights.md').write_text('\n'.join(lines), encoding='utf-8')
    bars = []
    for i, r in enumerate(sorted(ranking, key=lambda r:r['scenario'])):
        y = 52+i*48
        bars.append(f'<text x="12" y="{y+19}" fill="#dce6ef">S{r["scenario"]}</text><rect x="50" y="{y}" width="{r["otif"]*490:.1f}" height="27" rx="4" fill="#37c9ac"/><text x="{60+r["otif"]*490:.1f}" y="{y+19}" fill="#dce6ef">{r["otif"]:.1%}</text>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 650 315" role="img" aria-label="OTIF by recovery scenario"><rect width="650" height="315" fill="#112438"/><text x="12" y="28" fill="white" font-family="sans-serif" font-size="19">On-time in-full aircraft deliveries</text>'+''.join(bars)+'</svg>'
    (out/'scenario_otif.svg').write_text(svg, encoding='utf-8')
    rows = ''.join(f'<tr><td>S{r["scenario"]}</td><td>{escape(SCENARIOS[r["scenario"]])}</td><td>{r["otif"]:.1%}</td><td>{r["ending_backlog"]}</td><td>${r["recovery_cost"]:,.0f}</td><td>{r["weighted_score"]:.3f}</td></tr>' for r in ranking)
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AeroPlan | Recovery decision</title>
<style>body{{font:16px/1.6 system-ui;background:#091726;color:#dce6ef;margin:0;padding:5vw}}main{{max-width:1100px;margin:auto}}h1{{font-size:clamp(28px,5vw,52px);line-height:1.1}}.label{{color:#37c9ac;letter-spacing:.15em}}.cards{{display:flex;gap:16px;flex-wrap:wrap}}.card{{background:#112438;padding:24px;border-radius:12px;flex:1;min-width:180px}}strong{{font-size:28px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #294158}}.table{{overflow:auto}}svg{{max-width:700px;width:100%}}a{{color:#37c9ac}}.muted{{color:#acbccb}}</style>
<main><p class="label">AEROPLAN MANUFACTURING / SYNTHETIC IBP LAB</p><h1>Recover the plan.<br>Make the trade-off explicit.</h1><p class="muted">26-week finite planning simulation · Seed {cfg.seed} · No real company data</p>
<div class="cards"><div class="card">Balanced recommendation<br><strong>Scenario {winner['scenario']}</strong></div><div class="card">Recommended OTIF<br><strong>{winner['otif']:.1%}</strong></div><div class="card">Backlog exposure reduction<br><strong>{winner['backlog_reduction']:.1%}</strong></div></div>
<h2>Service is one part of the decision</h2>{svg}<div class="table"><table><tr><th>Rank order</th><th>Strategy</th><th>OTIF</th><th>End backlog</th><th>Recovery cost</th><th>Weighted score</th></tr>{rows}</table></div>
<p>Scores combine service, backlog exposure, inventory stability, cost and operational risk. All dollars are fictional incremental planning costs.</p><p><a href="executive_insights.md">Executive memo</a> · <a href="root_causes.json">Root-cause evidence</a> · <a href="csv/scenario_evaluation.csv">Decision data</a></p><p class="muted">A local generated report, not a Power BI dashboard. See ../powerbi/dashboard_spec.md for the four-page Power BI build specification.</p></main></html>'''
    (out/'index.html').write_text(html, encoding='utf-8')
