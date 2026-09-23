# Data dictionary

All data is synthetic. CSV headers equal SQLite column names. Flags are 0/1. Blank CSV cells map to NULL. Scenario IDs represent alternative worlds and must not be summed as one demand population.

## Datasets and exact fields

### `aircraft_bom`

**Grain:** product × component; units per aircraft.

**Seed-42 rows:** 9 (generated snapshot, not an input).

**Columns:** `product`, `component`, `quantity`.

### `capacity_execution`

**Grain:** scenario × week; FAL usage and weekly roll state.

**Seed-42 rows:** 156 (generated snapshot, not an input).

**Columns:** `scenario`, `week`, `available_hours`, `used_hours`, `unconstrained_load_hours`, `overload_hours`, `known_open_orders`, `rescheduling_enabled`.

### `component_risk_rank`

**Grain:** SQL view: scenario × component.

**Seed-42 rows:** 18 (generated snapshot, not an input).

**Columns:** `scenario`, `component`, `blocked_order_weeks`, `stockout_weeks`, `average_coverage`, `risk_rank`.

### `components`

**Grain:** component; unit/shipset definitions.

**Seed-42 rows:** 3 (generated snapshot, not an input).

**Columns:** `component`, `description`.

### `constraint_exceptions`

**Grain:** SQL view: scenario × week × resource × exception_type.

**Seed-42 rows:** 147 (generated snapshot, not an input).

**Columns:** `scenario`, `week`, `exception_type`, `resource`, `magnitude`, `unit`.

### `customer_orders`

**Grain:** Original order_id; one aircraft per order; incremental shock orders appear in order_fulfillment.

**Seed-42 rows:** 442 (generated snapshot, not an input).

**Columns:** `order_id`, `product`, `due_week`, `quantity`, `priority`, `known_week`, `incremental`.

### `demand_forecast`

**Grain:** vintage_week × target week × product.

**Seed-42 rows:** 1053 (generated snapshot, not an input).

**Columns:** `vintage_week`, `week`, `product`, `forecast_units`.

### `dim_release_week`

**Grain:** release_week; includes pre-horizon pipeline.

**Seed-42 rows:** 31 (generated snapshot, not an input).

**Columns:** `release_week`, `release_week_label`.

### `dim_scenario`

**Grain:** scenario; -1 reference, 0–4 disrupted alternatives.

**Seed-42 rows:** 6 (generated snapshot, not an input).

**Columns:** `scenario`, `scenario_name`.

### `dim_week`

**Grain:** week; 1–26.

**Seed-42 rows:** 26 (generated snapshot, not an input).

**Columns:** `week`, `week_label`, `phase`.

### `forecast_accuracy`

**Grain:** SQL view: scenario × week × product.

**Seed-42 rows:** 468 (generated snapshot, not an input).

**Columns:** `scenario`, `week`, `product`, `demand_units`, `forecast_units`, `absolute_error`, `rolling_4w_wape`.

### `inventory`

**Grain:** component; opening on-hand before Week 1 receipts.

**Seed-42 rows:** 3 (generated snapshot, not an input).

**Columns:** `component`, `opening_units`, `target_coverage_weeks`.

### `material_balance`

**Grain:** scenario × week × component.

**Seed-42 rows:** 468 (generated snapshot, not an input).

**Columns:** `scenario`, `week`, `component`, `opening_units`, `receipts`, `consumed`, `closing_units`, `coverage_weeks`, `stockout`, `blocked_orders`.

### `order_fulfillment`

**Grain:** scenario × order_id; original and incremental demand with terminal status.

**Seed-42 rows:** 2797 (generated snapshot, not an input).

**Columns:** `order_id`, `product`, `due_week`, `quantity`, `priority`, `known_week`, `incremental`, `scenario`, `delivery_week`, `on_time`, `late_or_open`, `delay_weeks`.

### `order_risk`

**Grain:** SQL view: scenario × late/open order.

**Seed-42 rows:** 739 (generated snapshot, not an input).

**Columns:** `scenario`, `order_id`, `product`, `due_week`, `delivery_week`, `priority`, `delay_weeks`, `status`, `review_sequence`.

### `planning_exceptions`

**Grain:** scenario × week × order_id × constraint_type × resource.

**Seed-42 rows:** 1612 (generated snapshot, not an input).

**Columns:** `scenario`, `week`, `order_id`, `product`, `constraint_type`, `resource`.

### `production_capacity`

**Grain:** week; shared FAL hours.

**Seed-42 rows:** 26 (generated snapshot, not an input).

**Columns:** `week`, `fal_capacity_hours`.

### `production_plan`

**Grain:** scenario × week × product.

**Seed-42 rows:** 468 (generated snapshot, not an input).

**Columns:** `scenario`, `week`, `product`, `demand_units`, `produced`, `baseline_plan`, `absolute_deviation`, `backlog`, `on_time_due`, `used_hours`.

### `products`

**Grain:** product; family and abstract FAL hours per aircraft.

**Seed-42 rows:** 3 (generated snapshot, not an input).

**Columns:** `product`, `description`, `fal_hours`.

### `scenario_evaluation`

**Grain:** scenario; S0–S4, full-horizon utilities and score.

**Seed-42 rows:** 5 (generated snapshot, not an input).

**Columns:** `scenario`, `demand_units`, `produced`, `otif`, `ending_backlog`, `backlog_unit_weeks`, `capacity_utilization`, `plan_adherence`, `wape`, `inventory_instability`, `inventory_stability`, `recovery_cost`, `operational_risk`, `stockout_component_weeks`, `overload_weeks`, `backlog_reduction`, `weighted_score`, `otif_utility`, `backlog_reduction_utility`, `inventory_stability_utility`, `recovery_cost_utility`, `operational_risk_utility`, `rank`.

### `scenario_metrics`

**Grain:** scenario; full-horizon calculated KPIs including reference.

**Seed-42 rows:** 6 (generated snapshot, not an input).

**Columns:** `scenario`, `demand_units`, `produced`, `otif`, `ending_backlog`, `backlog_unit_weeks`, `capacity_utilization`, `plan_adherence`, `wape`, `inventory_instability`, `inventory_stability`, `recovery_cost`, `operational_risk`, `stockout_component_weeks`, `overload_weeks`.

### `supplier_release_load`

**Grain:** SQL view: scenario × supplier × release_week, split modes deduplicated.

**Seed-42 rows:** 492 (generated snapshot, not an input).

**Columns:** `scenario`, `supplier`, `component`, `release_week`, `allocated_units`, `available_capacity`, `master_capacity`, `release_utilization`, `incremental_cost`.

### `suppliers`

**Grain:** supplier; immutable capacity, lead time and qualification.

**Seed-42 rows:** 4 (generated snapshot, not an input).

**Columns:** `supplier`, `component`, `weekly_capacity`, `manufacturing_weeks`, `secondary`, `qualified`.

### `supply_shipments`

**Grain:** scenario × supplier × release_week × mode.

**Seed-42 rows:** 508 (generated snapshot, not an input).

**Columns:** `scenario`, `supplier`, `component`, `release_week`, `arrival_week`, `mode`, `units`, `master_capacity`, `available_capacity`, `planned_primary_units`, `manufacturing_weeks`, `transit_weeks`, `opening_pipeline`, `incremental_cost`.

### `transportation`

**Grain:** supplier; existing lanes and express capacity.

**Seed-42 rows:** 4 (generated snapshot, not an input).

**Columns:** `supplier`, `standard_weeks`, `express_weeks`, `express_capacity`.

### `weekly_kpi`

**Grain:** SQL view: scenario × week.

**Seed-42 rows:** 156 (generated snapshot, not an input).

**Columns:** `scenario`, `week`, `demand_units`, `produced`, `on_time_due`, `backlog`, `baseline_plan`, `absolute_deviation`, `rolling_on_time`, `rolling_demand`, `previous_backlog`, `otif`, `rolling_4w_otif`, `backlog_change`, `used_hours`, `available_hours`, `overload_hours`, `capacity_utilization`, `plan_adherence`.

## Field units and semantics

|Field group|Meaning|
|---|---|
|scenario, scenario_name|Alternative ID/name; -1 is excluded from recovery ranking.|
|week, due_week, delivery_week, release_week, arrival_week, vintage_week, known_week|Relative integer weeks; pre-horizon releases may be ≤0. Null delivery means unfilled. Vintage/known dates prevent treating later information as available earlier.|
|product, component, supplier, order_id|Stable fictional business IDs. Product families share component types.|
|quantity, units, produced, demand_units, baseline_plan, on_time_due, backlog|Integer aircraft or component units according to table grain; BOM quantity is units per aircraft. Forecast_units is a decimal estimate.|
|fal_hours, used_hours, available_hours, fal_capacity_hours, unconstrained_load_hours, overload_hours|Abstract assembly workload hours. Unconstrained load includes all due/backlog demand before scheduling. Overload is max(load − available,0), not executed overbooking.|
|weekly_capacity, master_capacity, available_capacity, express_capacity|Units per source/release week. On split-mode shipment rows capacity repeats: use MAX or the deduplicated supplier_release_load view, never SUM.|
|manufacturing_weeks, standard_weeks, express_weeks, transit_weeks|Fixed integer lead times. Arrival = release + manufacturing + transit.|
|opening_units, receipts, consumed, closing_units|Material units: closing = opening + receipts − consumed. Next opening equals prior closing.|
|coverage_weeks, target_coverage_weeks, average_coverage|Forward-demand inventory coverage; NULL if future demand denominator is unavailable. Means exclude nulls.|
|priority|1 highest, 3 lowest; used by the recovery reprioritization policy.|
|incremental, secondary, qualified, opening_pipeline, rescheduling_enabled, stockout, on_time, late_or_open|0/1 flags. Stockout means zero closing stock, not necessarily an unfulfilled order. Late_or_open includes late deliveries.|
|known_open_orders|All known unfinished orders at roll start, including future-due commitments; not just overdue backlog.|
|constraint_type, resource, exception_type, magnitude, unit|Exception classification and explicitly labeled magnitude: material order-week events or FAL hours.|
|mode, planned_primary_units|Standard/express transport and requested primary consensus release before capacity loss. Planned units repeat across split modes; aggregate with MAX.|
|incremental_cost, recovery_cost|Fictional USD. Recovery cost includes shipment premiums plus the applicable resequencing proxy.|
|absolute_deviation, absolute_error, delay_weeks|Aircraft gap versus reference, forecast-demand error, and nonnegative delivery delay censored at horizon for open orders.|
|otif, rolling_4w_otif, capacity_utilization, release_utilization, plan_adherence, wape, rolling_4w_wape|Decimal ratios; reaggregate underlying numerators and denominators rather than averaging rates.|
|ending_backlog, backlog_unit_weeks, backlog_reduction|Final aircraft backlog, total aircraft-week exposure, relative exposure reduction versus S0.|
|previous_backlog, backlog_change, rolling_on_time, rolling_demand|Window-derived prior backlog, change and pooled four-week service counts.|
|blocked_orders, blocked_order_weeks, stockout_weeks, stockout_component_weeks, overload_weeks|Exception counts at the stated grain. Repeated blocks of one order are separate order-week events.|
|inventory_instability, inventory_stability, operational_risk|Documented dimensionless policy metrics; risk is not a probability.|
|*_utility, weighted_score, rank, risk_rank, review_sequence|Normalized [0,1] utility and weighted score; rank 1 best. Risk rank sorts block events descending. Review queue places open orders first.|
|status, phase, description, week_label, release_week_label|Human-readable categories; numeric week controls sort order.|

## Integrity and relationships

Unique SQLite indexes protect main fact business keys. Python validates master references, quantities, capacity, lead times, material/BOM conservation and backlog before export. SQLite runs PRAGMA integrity_check. This generated analytics store does not declare full foreign-key DDL for every denormalized fact. See the Power BI specification for explicit star-schema relationships; never join incompatible fact grains and sum repeated capacity.

## Other generated artifacts

- manifest.json: input configuration and SHA-256 hashes of every CSV; no nondeterministic timestamp.
- validation.json: per-scenario physical-check summary; regression tests run separately.
- root_causes.json: constraint evidence, receipt-deficit timing, at-risk IDs and isolated demand/capacity counterfactuals.
- sensitivity.json: policy weights and winner per preference profile.
- executive_insights.md, index.html and scenario_otif.svg: data-driven summaries of the same results.
