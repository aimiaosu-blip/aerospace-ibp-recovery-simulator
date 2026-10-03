# Planning and decision methodology

## Information and event ordering

1. Generate immutable masters and original orders using `random.Random(seed)`; no global random state.
2. Build vintage-1 consensus quantities as the larger of firm orders and rounded forecast. Convert through the BOM into dated requirements.
3. Offset those requirements by fixed manufacturing plus standard transportation lead time. Releases before Week 1 are the explicit opening pipeline; opening on-hand is additional stock.
4. For disrupted runs, announce extra AP-100 orders in Week 10. Original orders and data stay unchanged. The exact realized uplift is integer constrained: cumulative rounding keeps the added order count within half an aircraft of the configured percentage.
5. Lower S-A1 availability from 20 to 12 release units in Weeks 10–13 (40%), leaving the master at 20. The release-to-arrival offset is five weeks on the standard lane, producing Weeks 15–18 deficits.
6. Apply each scenario's permitted recovery levers to releases from Week 10. No pre-Week-10 action or retroactive acceleration of in-transit units is allowed.
7. At each weekly roll, add receipts, identify known outstanding orders, calculate unconstrained due/backlog load, schedule feasible indivisible aircraft, deduct BOM consumption, record completions, and carry stock and unfinished orders forward.
8. Analyze the ledger and compare alternatives against the same disrupted order population. Scenario -1 is a reference benchmark with a different, undisrupted demand population and is excluded from decision ranking.

This is a fixed-end 26-week experiment, not an infinite-horizon planner. The archived forecast vintages demonstrate data structure and can support future forecast-refresh extensions; they do not imply the current committed supply policy refreshes every vintage. Firm orders determine the execution queue. A full rolling-horizon optimizer with appended future weeks is a future extension.

## Feasible scheduling heuristic

- Normal policy: sort by due week, then stable order ID. Only due or overdue orders are eligible.
- Rescheduling policy: first due/overdue versus future due, then business priority (1 highest), due week and ID. Future known orders are eligible at most two weeks early and only after due/backlog candidates have been considered.
- Check every BOM component and shared FAL hours before completing an aircraft. An infeasible order is skipped rather than stopping all other work.
- Component shortage and FAL overload can co-occur. The exception ledger can record both for a blocked order. The model does not force a unique causal attribution.
- No overtime is silently introduced. If due load is above FAL capacity, excess demand stays in backlog. Executed usage is always at or below capacity.
- Assembly and delivery are represented in the same weekly bucket. There is no partially completed WIP, customer acceptance lag or finished-goods warehouse. Early completion counts as accepted early delivery.

## Supply recovery rules

S1/S4 expedite up to the fixed express capacity per supplier/release week. Remainder travels on the standard lane. Total material volume is unchanged by expediting. All manufacturing lead time remains intact.

S2/S4 allocate `min(secondary capacity, primary shortfall + incremental AP-100 requirement)` to the existing S-A2 lane. No source is added or qualified. S-A2 starts at zero baseline allocation but its qualification, capacity and route exist before the experiment. This represents pre-existing reserved planning headroom. Incremental engine/avionics shortages are not automatically recovered by an airframe action, a deliberate scope constraint visible in results.

There is no blanket ordering of “S4 always best”: weights, costs, seeds and planning limits can change the decision. Fixed transport/master parameters are inputs; the planner may choose among those options but cannot rewrite them.

## Exact KPI definitions

Let `w` denote week, `p` product, `s` scenario, `c` component, `D` due demand and `X` completed aircraft.

- **OTIF:** `sum(complete_delivery_week <= due_week) / count(all due orders)`. All one-aircraft orders are in full on completion. Undelivered orders are failures; early deliveries are successes. The weekly value is grouped by **due week**, not delivery week. Rolling four-week OTIF pools both counts across four weeks; it is not an average of percentages.
- **Backlog:** count orders with `due_week <= w` that have not completed by `w`. If `E(w)` is completed future-due demand, then `backlog(w) = cumulative D − cumulative X + E(w)`. Ending backlog takes only the final selected week.
- **Exposure:** `sum_w backlog(w)`, in aircraft-weeks. Reduction relative to S0 is `(S0 exposure − scenario exposure) / S0 exposure`. If S0 exposure is zero, reduction is neutral zero for every alternative.
- **FAL utilization:** `sum used_hours / sum available_hours`. Capacity is a shared factory fact, not a per-product denominator. Product-filtered hours must be labeled as contribution to the factory pool.
- **Unconstrained overload:** `max(0, hours of pending due/backlog orders before scheduling − available hours)`. This can include orders simultaneously blocked by material; it is not proof that adding FAL hours alone would fix the backlog.
- **Adherence:** `max(0, 1 − sum(abs(X_s,p,w − X_reference,p,w)) / sum(X_reference,p,w))`. Both over- and under-production count as deviation. This is a portfolio metric definition, not a universal corporate standard.
- **Coverage:** `closing_stock_c,w / mean(BOM demand over w+1 ... min(w+4,26))`, using only orders known at `w`. Exclude the current week. Blank/NULL if there are no remaining weeks or no future demand. Ending-horizon coverage is not artificially set to zero.
- **Stockout:** closing inventory equals zero. A zero balance without a blocked order need not be a service failure; `blocked_orders` is the shortage evidence.
- **WAPE:** `sum(abs(vintage1_forecast_p,w − actual_s,p,w)) / sum(actual_s,p,w)`. “Actual” here is synthetic booked order demand, not produced units, external sales or realized consumption. Later forecast vintages are not substituted after observing the shock.
- **Inventory instability:** population standard deviation of valid coverage observations plus mean absolute deviation from the component's target coverage. Pooled across components and weeks; each component-week has equal weight. Stability = `1 / (1 + instability)`. Target coverage is 0.5 weeks in the default synthetic master.
- **Incremental recovery cost:** express units × $18,000 + secondary units × $26,000 + resequencing equivalent units × $6,000 (S3/S4 only). Resequencing equivalent units = post-event `sum(abs(family-week output − reference)) / 2`. This is an effort proxy; it can be fractional and includes output shortfall as well as timing shifts. It is not an exact count of rescheduled orders. No total-cost or savings claim is made.
- **Operational risk proxy:** `min(1, .50 × late/open order fraction + .25 × express airframe unit share + .15 × secondary airframe unit share + .10 × min(1, changed-equivalent units / reference output))`. Unit shares use airframe releases from Week 10 as denominator. Coefficients are fictional judgment inputs, not calibrated probabilities. OTIF and this proxy partly overlap, intentionally exposing residual service risk; users should review that preference.
- **Delay:** max(0, delivery week − due week); for open orders substitute Week 26. This is a censored lower bound, not an estimated future delivery date.

## Scoring and robustness

For each criterion, normalize to [0,1] over S0–S4. Benefits use `(value − minimum)/(maximum − minimum)`; cost and risk reverse that utility. Equal-valued criteria receive 1 for all alternatives and cannot affect their relative order. Weighted score is the sum of utility × weight; weights must be nonnegative, include all five criteria, and sum to one. Ties prefer lower recovery cost, then scenario ID.

|Preference|OTIF|Backlog reduction|Inventory stability|Cost|Risk|
|---|---:|---:|---:|---:|---:|
|Balanced|30%|25%|15%|20%|10%|
|Service first|45%|30%|10%|5%|10%|
|Cost cautious|20%|15%|10%|40%|15%|

Min-max scores can change when an alternative is added; they are not absolute performance ratings. The exercise contains deterministic parameter sensitivity, not Monte Carlo confidence intervals. Changing the seed regenerates forecast noise and priorities. It does not sample arbitrary macroeconomic events.

## Automated root-cause analysis

The module identifies the largest material block-event count, sources whose available capacity is below master capacity, the family with the most late/open orders, explicit at-risk order IDs, zero-stock weeks, overload weeks and receipt deficits against reference. An earlier material block can be caused by new demand before the supplier's physical shortfall arrives.

Two additional no-action counterfactuals isolate demand uplift alone and source loss alone, keeping all other settings and the same original data fixed. Their impacts need not add because inventory buffers and finite scheduling interact. This provides explanatory evidence rather than a claim of rigorous structural causal identification.

## Export precision

Floating-point values are serialized to ten decimal places in CSV, JSON and SQLite for stable cross-version evidence. This does not round aircraft/component counts. Presentation percentages are rounded separately; source ratios remain available for reconciliation.

## Known limits and useful extensions

The model omits detailed aircraft configurations, multi-stage assembly, WIP, yields, cash flow, contract penalties, stochastic transit failures and finite upstream work-center loading. A next iteration could add customer promise dates, a genuine rolling 26-week optimization horizon, mixed-integer scheduling and stress-tested cost distributions. Any extension must preserve scope: source qualification and supplier creation remain outside the IBP planner's authority.


## Portfolio Complexity & Cost Analytics

This is a **synthetic independent portfolio project**, unrelated to any employer's data, product design, supplier agreements or achieved savings. Aircraft labels, variant mappings, qualifications, costs and lifecycle values are fictional. It demonstrates a transferable analysis method for cost of portfolio complexity; it is not an Ericsson case study.

### Controlled experiments

`aeroplan.portfolio.masters` constructs four complete, independent master-data snapshots before running the existing `simulate` engine. All use the same seed, unit aircraft orders, forecast vintages, disruption and integrated recovery policy (scenario 4); each has its own undisrupted reference. Existing recovery scenarios remain unchanged. The engine now supports sparse BOMs (absent component requirements mean zero); all existing conservation and capacity validations still apply.

| Portfolio | Actual master-data intervention |
|---|---|
| Baseline | AIRFRAME common; three aircraft-specific ENGINE and three AVIONICS variants, seven active items. Dedicated engine capacities 28/11/5 and avionics capacities 14/5/3. |
| Standardization | Merge the three avionics variants into one common item with capacity 22; replace the BOM, suppliers, routes and inventory; five items. |
| Consolidation | Retain seven items; group engine vendors and avionics vendors separately; reduce each non-airframe item source capacity by one unit/week and extend standard transit by one week. Capacity stays item-specific, not a shared vendor pool. |
| Global Product Adoption | Also merge engines into one common item with capacity 44; engine and avionics share a fictional vendor group; three items. |

Merging preserves physical BOM demand: each aircraft still needs one airframe, two engines, one avionics shipset. Dedicated variants carry one opening shipset each; a pooled family carries two. AIRFRAME stock and its disruption/secondary source rules are preserved. Common items assume maturity 1; dedicated variants assume maturity .9/.7/.3. These are **ex ante synthetic assumptions, not consequences proven by standardization**. Supplier vendor groups model correlated exposure and administration only; capacity constraints remain source/item-specific. Opening supply pipelines are rebuilt from each scenario's lead times, so these are steady-state alternative designs, not an in-flight migration simulation. Conversion cost is illustrative; transition downtime is not simulated.

### Indicators and configurable index

Active items = modeled component count; variants = active items minus functional families. Low-volume ratio = share with horizon gross requirements below 150 units. Gross requirements are derived from all disrupted aircraft orders and the scenario BOM, not actual fulfilled consumption. Supplier fragmentation = `1 - sum(capacity_share_by_vendor_group ** 2)` (capacity in component units; an illustrative exposure measure, not spend concentration). Lifecycle maturity = unweighted item mean. Order frequency = mean share of weeks with positive gross requirements; it measures replenishment touchpoints, not actual purchase-order counts. Demand variability = mean item population standard deviation / mean weekly gross requirements, including zero weeks. Cross-aircraft commonality = mean `(aircraft_count - 1) / (number_of_aircraft_types - 1)`. Exception frequency = constraint event count / (aircraft orders × horizon weeks); multiple component and capacity events per order-week may occur, so this is not a probability.

The nine index dimensions are active items, variants, low-volume ratio, supplier fragmentation, **1 − maturity**, order frequency, demand variability, **1 − commonality**, exception frequency. `index = 100 × sum(weight × min(1, raw / scale))`. Default equal weights are 1/9; scales are 7, 4, 1, 1, 1, 1, 1, 1, 1. All directions mean greater modeled complexity. Scales are fixed across portfolios; index contributions are saved in `assumptions.json`. This mixes structural inputs and an execution outcome (exceptions), so the index is descriptive, not an independent causal predictor. Configurations reject negative/nonfinite costs, invalid scales and weights not summing to one.

Override coefficients using `python -m aeroplan --portfolio-config policy.json`. JSON keys map to `PortfolioConfig`; when overriding weights/scales supply all nine keys. Example: `{"item_admin_cost": 1500, "holding_rate_per_week": 0.003}`. Configuration and seed are exported for replay. Scenario transformations are explicit in `masters`, not learned or secretly outcome-adjusted.

### Cost of Complexity (illustrative USD)

All fixed fees apply once over the modeled horizon, with no annualization. Item administration = active items × 1,200; supplier administration = distinct vendor groups × 2,400; exception handling = every logged constraint event × 35; lifecycle support = sum(1 − maturity) × 900. Holding cost = sum of weekly closing stock × synthetic item value × .002/week, using values 100,000/60,000/20,000 for airframe/engine/avionics. Conversion = removed items versus seven-item baseline × 8,000. Their sum is `cost_of_complexity`. These are scoped modeled costs, not all causally incremental costs of complexity. `total_modeled_cost` adds the existing engine's recovery cost exactly once. Recovery cost remains express/secondary allocation/resequencing cost; no procurement principal, lost-sales valuation, revenue, real quotes or total lifecycle cost is claimed. Separate breakdowns allow users to change or challenge each assumption.

Average inventory = sum weekly closing component units / weeks (sum across items, not average per SKU). OTIF and backlog retain the existing unit-order definitions. Exceptions count repeat events, not unique delayed orders. Standardization proxy equals commonality. Flexibility proxy = retained active items / seven baseline items, representing variant choice only, not scheduling agility. Resilience proxy equals vendor diversification (1 − HHI), not tested outage resilience or an estimated probability. Global commonality can increase pooling while reducing vendor diversification. These opposing dimensions are reported separately; no weighted overall portfolio winner is asserted. `cost_rank` sorts ascending total modeled cost, with scenario-name tie break; service and proxies are excluded from that ranking.

### Evidence and AI boundary

Each portfolio exports master data, full IBP ledgers and invariant validation. `evidence.json` contains immutable comparison rows and index/cost audits with stable scenario-keyed evidence IDs and source digests. Python owns all indicators, costs and ranking. Existing SQL owns original IBP reporting. Portfolio calculations reuse Python rather than duplicate formulas in SQL. Existing `select_insights`/optional Ollama selector receives a deep copy and may return candidate IDs only. It cannot submit prose, numbers, KPI edits or ranking changes. Invalid schemas, unknown IDs, missing categories and offline adapter errors select deterministic fallback interpretations. All numbers are generated without a model; no live model is required or claimed in the default run.
