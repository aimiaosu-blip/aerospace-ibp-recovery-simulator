# Executive decision brief

> Entirely synthetic AeroPlan Manufacturing simulation. No Airbus data, affiliation or SAP implementation.

Recommend **Scenario 4: Integrated recovery** under the balanced weights.
Its weighted score is 0.702; OTIF is 88.3%, versus 52.4% with no action.
Backlog exposure falls by 67.2%; incremental recovery cost is 4,035,000 fictional USD.

## Decision table

|Scenario|OTIF|End backlog|Backlog unit-weeks|Cost (USD)|Risk proxy|Score|
|---|---:|---:|---:|---:|---:|---:|
|0 — No action|52.4%|43|393|0|0.242|0.256|
|1 — Expedite transportation|58.2%|43|266|2,592,000|0.399|0.369|
|2 — Existing secondary allocation|63.7%|18|171|780,000|0.205|0.681|
|3 — FAL rescheduling and priority|80.5%|43|393|168,000|0.104|0.526|
|4 — Integrated recovery|88.3%|18|129|4,035,000|0.276|0.702|

## Diagnosis and action

First supplier-driven receipt deficit is in Week 15; earlier blocking can reflect demand pressure and opening buffers.
The event ledger identifies **AIRFRAME** as the largest material blocker and **S-A1** as the capacity-reduced source.
The largest late/open order count is in **AP-100**. First material blocking occurs in Week 14.
Demand exceeds available FAL hours in 11 weeks under Scenario 0; the executed plan never exceeds FAL capacity.
There are 224 late or horizon-open orders in Scenario 0. Inspect `root_causes.json` and `csv/order_risk.csv` for traceable IDs.

## Sensitivity and governance

- Counterfactual demand_only: OTIF 72.6%, backlog exposure 129 aircraft-weeks. These effects need not add linearly.
- Counterfactual capacity_only: OTIF 64.0%, backlog exposure 159 aircraft-weeks. These effects need not add linearly.
- balanced: Scenario 4 ranks first.
- service_first: Scenario 4 ranks first.
- cost_cautious: Scenario 2 ranks first.

Authorize only the selected planning levers within existing master-data limits. Review the order-risk queue weekly, monitor airframe receipt timing, and revisit weights with the decision owner.
Costs and operational risk are illustrative policy inputs, not supplier quotes or calibrated failure probabilities. Min-max scores depend on the alternatives included.
Ending backlog excludes orders after the horizon; late/open order delay is censored at the horizon. Forecast accuracy compares vintage 1 against synthetic orders, not real customer consumption.
