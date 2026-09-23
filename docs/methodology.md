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
