"""Synthetic portfolio experiments, with real master-data -> IBP propagation."""
import copy
import html
import json
import math
from collections import Counter
from dataclasses import dataclass, asdict, field
from statistics import mean, pstdev
from pathlib import Path
from .planning import simulate
from .analysis import metrics
from .validation import validate_inputs, validate_result
from .insights import digest, select_insights
from .storage import canonical, write_csv, write_json

SCENARIOS = ('Baseline', 'Standardization', 'Consolidation', 'Global Product Adoption')
INDICATORS = ('active_items', 'variants', 'low_volume_ratio', 'supplier_fragmentation',
              'lifecycle_immaturity', 'order_frequency', 'demand_variability',
              'lack_of_commonality', 'exception_frequency')

@dataclass(frozen=True)
class PortfolioConfig:
    """Illustrative coefficients only: USD per modeled 26-week horizon, not estimates."""
    weights: dict = field(default_factory=lambda: dict.fromkeys(INDICATORS, 1/9))
    scales: dict = field(default_factory=lambda: dict(zip(INDICATORS, (7, 4, 1, 1, 1, 1, 1, 1, 1))))
    low_volume_units: int = 150
    item_admin_cost: float = 1200
    supplier_admin_cost: float = 2400
    exception_cost: float = 35
    holding_rate_per_week: float = .002
    immature_item_cost: float = 900
    conversion_cost_per_removed_item: float = 8000
    def __post_init__(self):
        if set(self.weights) != set(INDICATORS) or set(self.scales) != set(INDICATORS):
            raise ValueError('All index dimensions required')
        if any(not math.isfinite(v) or v < 0 for v in self.weights.values()) or abs(sum(self.weights.values())-1)>1e-9:
            raise ValueError('Finite nonnegative weights must sum to one')
        if any(not math.isfinite(v) or v <= 0 for v in self.scales.values()):
            raise ValueError('Finite positive normalization scales required')
        for key, value in asdict(self).items():
            if key not in ('weights', 'scales') and (not math.isfinite(value) or value < 0):
                raise ValueError('Thresholds and costs must be finite and nonnegative')


def masters(base, scenario):
    """Split engine/avionics variants by aircraft; merge selected families ex ante.

    AIRFRAME retains the engine's fixed disruption and qualified secondary source.
    Consolidation groups vendor identities but preserves independent capacity per item.
    No capacity or lead-time benefit is inferred from vendor consolidation.
    """
    if scenario not in SCENARIOS:
        raise ValueError('Unknown portfolio scenario')
    data = copy.deepcopy(base)
    products = [p['product'] for p in base['products']]
    merged = {'AIRFRAME'}
    if scenario in ('Standardization', 'Global Product Adoption'):
        merged.add('AVIONICS')
    if scenario == 'Global Product Adoption':
        merged.add('ENGINE')
    data.update({key: [] for key in ('components', 'aircraft_bom', 'inventory', 'suppliers', 'transportation')})
    items = []
    capacities = {'ENGINE': (28, 11, 5), 'AVIONICS': (14, 5, 3)}
    unit_values = {'AIRFRAME': 100000, 'ENGINE': 60000, 'AVIONICS': 20000}
    for family in ('AIRFRAME', 'ENGINE', 'AVIONICS'):
        groups = [products] if family in merged else [[p] for p in products]
        for i, group in enumerate(groups):
            component = family if len(groups)==1 else family+'-'+group[0]
            data['components'].append({'component': component, 'description': 'Synthetic '+component})
            for p in group:
                data['aircraft_bom'].append({'product':p, 'component':component, 'quantity':2 if family=='ENGINE' else 1})
            original = next(r for r in base['inventory'] if r['component']==family)
            # Dedicated variants each carry one shipset; pooled stock carries two.
            opening = original['opening_units'] if family=='AIRFRAME' else (2 if family=='ENGINE' else 1)*(2 if len(groups)==1 else 1)
            data['inventory'].append(dict(original, component=component, opening_units=opening))
            items.append({'component':component, 'family':family, 'active':1,
                          'lifecycle_maturity':1.0 if len(groups)==1 else (.9,.7,.3)[i],
                          'aircraft_count':len(group), 'unit_value':unit_values[family]})
            for source in [s for s in base['suppliers'] if s['component']==family]:
                s=copy.deepcopy(source)
                if len(groups)>1:
                    s['supplier'] += '-'+group[0]
                    s['weekly_capacity']=capacities[family][i]
                s['component']=component
                s['vendor_group'] = ('GLOBAL-VENDOR' if scenario=='Global Product Adoption' and family!='AIRFRAME'
                                     else family+'-VENDOR' if scenario=='Consolidation' and family!='AIRFRAME'
                                     else s['supplier'])
                route=next(r for r in base['transportation'] if r['supplier']==source['supplier'])
                data['transportation'].append(dict(route,supplier=s['supplier']))
                # Consolidation trades lower vendor administration for a longer delivery route.
                if scenario=='Consolidation' and family!='AIRFRAME':
                    data['transportation'][-1]['standard_weeks'] += 1
                    s['weekly_capacity']=max(1, s['weekly_capacity']-1)
                data['suppliers'].append(s)
    return data, items


def indicators(data, items, result, cfg, policy):
    bom={(r['product'],r['component']):r['quantity'] for r in data['aircraft_bom']}
    demand={i['component']:[sum(bom.get((o['product'],i['component']),0) for o in result['orders'] if o['due_week']==w)
                           for w in range(1,cfg.weeks+1)] for i in items}
    vendors=Counter()
    for s in data['suppliers']:
        vendors[s['vendor_group']]+=s['weekly_capacity']
    total=sum(vendors.values())
    fragmentation=1-sum((v/total)**2 for v in vendors.values()) if total else 0
    commonality=mean((i['aircraft_count']-1)/max(1,len(data['products'])-1) for i in items)
    maturity=mean(i['lifecycle_maturity'] for i in items)
    raw=dict(active_items=len(items),variants=len(items)-len({i['family'] for i in items}),
             low_volume_ratio=mean(sum(v)<policy.low_volume_units for v in demand.values()),
             supplier_fragmentation=fragmentation,lifecycle_immaturity=1-maturity,
             order_frequency=mean(sum(x>0 for x in v)/cfg.weeks for v in demand.values()),
             demand_variability=mean(pstdev(v)/mean(v) if mean(v) else 0 for v in demand.values()),
             lack_of_commonality=1-commonality,
             exception_frequency=len(result['exceptions'])/max(1,len(result['orders'])*cfg.weeks))
    contributions={k:policy.weights[k]*min(1,raw[k]/policy.scales[k]) for k in INDICATORS}
    return dict(raw, lifecycle_maturity=maturity,cross_aircraft_commonality=commonality,
                complexity_index=100*sum(contributions.values())), contributions


def costs(data, items, result, policy, baseline_items=7):
    values={i['component']:i['unit_value'] for i in items}
    parts={'item_administration':len(items)*policy.item_admin_cost,
           'supplier_administration':len({s['vendor_group'] for s in data['suppliers']})*policy.supplier_admin_cost,
           'exception_handling':len(result['exceptions'])*policy.exception_cost,
           'inventory_holding':sum(r['closing_units']*values[r['component']]*policy.holding_rate_per_week for r in result['material']),
           'lifecycle_support':sum(1-i['lifecycle_maturity'] for i in items)*policy.immature_item_cost,
           'conversion':max(0,baseline_items-len(items))*policy.conversion_cost_per_removed_item}
    return parts


def run_portfolio(base, cfg, out, selector=None, policy=None):
    policy=policy or PortfolioConfig()
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    rows=[]; facts={}; candidates=[]; audits={}
    for scenario in SCENARIOS:
        data,items=masters(base,scenario)
        validate_inputs(data,cfg)
        reference=simulate(data,cfg)
        result=simulate(data,cfg,4,reference)
        validation=validate_result(result,data,cfg,reference)
        kpi=metrics(result,data,cfg,4)
        raw,contributions=indicators(data,items,result,cfg,policy)
        breakdown=costs(data,items,result,policy)
        row=dict(portfolio_scenario=scenario,**raw,
                 average_inventory_units=sum(r['closing_units'] for r in result['material'])/cfg.weeks,
                 ending_inventory_units=sum(r['closing_units'] for r in result['material'] if r['week']==cfg.weeks),
                 otif=kpi['otif'],ending_backlog=kpi['ending_backlog'],backlog_unit_weeks=kpi['backlog_unit_weeks'],
                 exceptions=len(result['exceptions']),recovery_cost=kpi['recovery_cost'],
                 cost_of_complexity=sum(breakdown.values()),
                 total_modeled_cost=sum(breakdown.values())+kpi['recovery_cost'],
                 standardization_proxy=raw['cross_aircraft_commonality'],
                 flexibility_proxy=len(items)/7,
                 resilience_proxy=raw['supplier_fragmentation'])
        rows.append(row)
        slug=scenario.lower().replace(' ','_')
        folder=out/slug
        write_json(folder/'master_data.json',data)
        write_json(folder/'ibp_result.json',result)
        write_json(folder/'validation.json',validation)
        for name,records in dict(data,portfolio_items=items,**result).items():
            write_csv(folder/(name+'.csv'),records)
        audits[scenario]={'master_digest':digest(data),'result_digest':digest(result),
                          'index_contributions':contributions,'cost_breakdown':breakdown}
    # Explicit reporting order, not a claim of multi-objective optimality.
    for rank,row in enumerate(sorted(rows,key=lambda r:(r['total_modeled_cost'],r['portfolio_scenario'])),1):
        row['cost_rank']=rank
    for row in rows:
        name=row['portfolio_scenario']; sid='portfolio_comparison:'+name
        facts[sid]={'table':'portfolio_comparison','key':{'portfolio_scenario':name},
                    'record':copy.deepcopy(row),'csv':'comparison.csv'}
        write_json(out/name.lower().replace(' ','_')/'audit.json', audits[name])
        aid='portfolio_assumptions:'+name
        facts[aid]={'record':audits[name], 'json':name.lower().replace(' ','_')+'/audit.json'}
        candidates.append({'id':'portfolio_tradeoff:'+name,'kind':'portfolio_tradeoff:'+name,
                           'interpretation':name+': compare modeled cost and service with commonality, retained variant choice and vendor diversification. Proxies are not calibrated resilience probabilities; all coefficients and portfolio changes are synthetic.',
                           'evidence_ids':[sid,aid]})
    package=canonical({'schema_version':1,'synthetic_only':True,'source_digest':digest({'rows':rows,'audit':audits}),
                       'calculated_facts':facts,'candidates':candidates})
    insights=select_insights(package,selector)
    write_csv(out/'index_contributions.csv', [dict(portfolio_scenario=name, indicator=k, weighted_contribution=v) for name,a in audits.items() for k,v in a['index_contributions'].items()])
    write_csv(out/'cost_breakdown.csv', [dict(portfolio_scenario=name, cost_component=k, synthetic_usd=v) for name,a in audits.items() for k,v in a['cost_breakdown'].items()])
    write_csv(out/'comparison.csv',rows)
    write_json(out/'comparison.json',rows)
    write_json(out/'assumptions.json',{'synthetic_only':True,'policy':asdict(policy),'recovery_policy':4,'seed':cfg.seed,'weeks':cfg.weeks,'audit':audits})
    write_json(out/'evidence.json',package)
    write_json(out/'ai_insights.json',insights)
    columns=('portfolio_scenario','complexity_index','total_modeled_cost','otif','ending_backlog','average_inventory_units','exceptions','recovery_cost','standardization_proxy','flexibility_proxy','resilience_proxy','cost_rank')
    lines=['# Portfolio Complexity & Cost Analytics','','Synthetic independent portfolio project. No company data, calibrated costs or realized savings.',
           'All four portfolios rerun the same IBP engine with integrated recovery (4). Cost rank sorts total modeled cost only; it is not a recommendation.','',
           '| '+' | '.join(columns)+' |','|'+'|'.join(['---']*len(columns))+'|']
    for r in rows:
        lines.append('| '+' | '.join(str(round(r[k],4)) if isinstance(r[k],float) else str(r[k]) for k in columns)+' |')
    lines += ['', '## Evidence-linked interpretation', 'Mode: '+insights['mode']]
    for r in insights['interpretations']:
        lines += ['',r['interpretation'],'Evidence: '+', '.join(r['evidence_ids'])]
    write_json(out/'tradeoff.json',[{k:r[k] for k in ('portfolio_scenario','total_modeled_cost','standardization_proxy','flexibility_proxy','resilience_proxy')} for r in rows])
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    table='<table><thead><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in columns)+'</tr></thead><tbody>'
    for r in rows:
        table+='<tr>'+''.join('<td>'+html.escape(str(round(r[k],4) if isinstance(r[k],float) else r[k]))+'</td>' for k in columns)+'</tr>'
    table+='</tbody></table>'
    bars=''
    for r in rows:
        bars+='<h3>'+html.escape(r['portfolio_scenario'])+'</h3>'
        for k in ('standardization_proxy','flexibility_proxy','resilience_proxy'):
            bars+=f'<label>{k}: {r[k]:.3f} <meter min="0" max="1" value="{r[k]}"></meter></label><br>'
    (out/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Portfolio trade-offs</title><style>body{font:16px system-ui;margin:32px;color:#163047}table{border-collapse:collapse;font-size:12px}td,th{padding:9px;border:1px solid #ccd}th{background:#eaf2f6}section{overflow:auto}meter{width:240px}</style><h1>Portfolio Complexity & Cost Analytics</h1><p>Synthetic independent portfolio project. USD assumptions, not realized savings. Cost rank is cost-only.</p><section>'+table+'</section><h2>Standardization / flexibility / resilience trade-offs</h2>'+bars+'<p><a href="report.md">Report</a> · <a href="evidence.json">Evidence</a> · <a href="assumptions.json">Assumptions and formulas inputs</a> · <a href="comparison.csv">CSV</a></p></html>',encoding='utf-8')
    return {'rows':canonical(rows),'package':package,'insights':insights,'audit':audits}
