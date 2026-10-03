# AI-assisted planning insights

> Synthetic data only. Human review required.

Mode: `deterministic_fallback`
Fallback reason: `no_llm_requested`

## Interpretation — rule-authored; optionally selected by local LLM

LLM selection changes briefing emphasis only. The planning engine owns all numbers and ranking.

### demand_capacity:0:16

Due/backlog demand exceeds available assembly hours. Delivery pressure is present; this diagnostic does not mean the executed plan exceeds capacity.

**Calculated facts (Python/SQL; not AI-generated):**

- [capacity_execution:0:16](csv/capacity_execution.csv): `{"available_hours": 25.0, "known_open_orders": 226, "overload_hours": 11.0, "rescheduling_enabled": 0, "scenario": 0, "unconstrained_load_hours": 36.0, "used_hours": 16.0, "week": 16}`
- [production_plan:0:16:AP-100](csv/production_plan.csv): `{"absolute_deviation": 6, "backlog": 10, "baseline_plan": 12, "demand_units": 13, "on_time_due": 3, "produced": 6, "product": "AP-100", "scenario": 0, "used_hours": 6.0, "week": 16}`
- [production_plan:0:16:AP-200](csv/production_plan.csv): `{"absolute_deviation": 0, "backlog": 4, "baseline_plan": 4, "demand_units": 4, "on_time_due": 0, "produced": 4, "product": "AP-200", "scenario": 0, "used_hours": 6.0, "week": 16}`
- [production_plan:0:16:AP-300](csv/production_plan.csv): `{"absolute_deviation": 0, "backlog": 2, "baseline_plan": 2, "demand_units": 2, "on_time_due": 0, "produced": 2, "product": "AP-300", "scenario": 0, "used_hours": 4.0, "week": 16}`

### material_shortage:0:14:AIRFRAME

Material availability blocks due orders during scheduling. Inspect linked order outcomes before assigning delivery impact; repeated weeks are not distinct orders.

**Calculated facts (Python/SQL; not AI-generated):**

- [material_balance:0:14:AIRFRAME](csv/material_balance.csv): `{"blocked_orders": 1, "closing_units": 0, "component": "AIRFRAME", "consumed": 19, "coverage_weeks": 0.0, "opening_units": 1, "receipts": 18, "scenario": 0, "stockout": 1, "week": 14}`
- [order_fulfillment:0:X14-02](csv/order_fulfillment.csv): `{"delay_weeks": 1, "delivery_week": 15, "due_week": 14, "incremental": 1, "known_week": 10, "late_or_open": 1, "on_time": 0, "order_id": "X14-02", "priority": 1, "product": "AP-100", "quantity": 1, "scenario": 0}`
- [planning_exceptions:0:14:X14-02:material:AIRFRAME](csv/planning_exceptions.csv): `{"constraint_type": "material", "order_id": "X14-02", "product": "AP-100", "resource": "AIRFRAME", "scenario": 0, "week": 14}`

### supply_risk:0:S-A1:10:standard

Reduced source release capacity and downstream arrival-week inventory warrant joint review. Timing association alone does not establish the cause of every shortage.

**Calculated facts (Python/SQL; not AI-generated):**

- [material_balance:0:15:AIRFRAME](csv/material_balance.csv): `{"blocked_orders": 9, "closing_units": 0, "component": "AIRFRAME", "consumed": 12, "coverage_weeks": 0.0, "opening_units": 0, "receipts": 12, "scenario": 0, "stockout": 1, "week": 15}`
- [supply_shipments:0:S-A1:10:standard](csv/supply_shipments.csv): `{"arrival_week": 15, "available_capacity": 12, "component": "AIRFRAME", "incremental_cost": 0, "manufacturing_weeks": 3, "master_capacity": 20, "mode": "standard", "opening_pipeline": 0, "planned_primary_units": 19, "release_week": 10, "scenario": 0, "supplier": "S-A1", "transit_weeks": 2, "units": 12}`

### inventory_backlog:0:15:AP-100

Backlog coexists with remaining component inventory. Stock in one component cannot establish complete-kit availability; review material and assembly constraints before increasing buffers. Holding cost is not modeled.

**Calculated facts (Python/SQL; not AI-generated):**

- [material_balance:0:15:AVIONICS](csv/material_balance.csv): `{"blocked_orders": 0, "closing_units": 7, "component": "AVIONICS", "consumed": 12, "coverage_weeks": 0.3544303797, "opening_units": 0, "receipts": 19, "scenario": 0, "stockout": 0, "week": 15}`
- [material_balance:0:15:ENGINE](csv/material_balance.csv): `{"blocked_orders": 0, "closing_units": 14, "component": "ENGINE", "consumed": 24, "coverage_weeks": 0.3544303797, "opening_units": 0, "receipts": 38, "scenario": 0, "stockout": 0, "week": 15}`
- [production_plan:0:15:AP-100](csv/production_plan.csv): `{"absolute_deviation": 0, "backlog": 3, "baseline_plan": 12, "demand_units": 14, "on_time_due": 11, "produced": 12, "product": "AP-100", "scenario": 0, "used_hours": 12.0, "week": 15}`

### recovery_tradeoff:1

Compared with no action: OTIF higher; backlog exposure lower; ending backlog unchanged; recovery cost higher; risk proxy higher. The calculated ranking reflects policy weights, not an AI recommendation or proven optimum. Unpriced holding and delay effects are not lifecycle cost savings.

**Calculated facts (Python/SQL; not AI-generated):**

- [scenario_evaluation:1](csv/scenario_evaluation.csv): `{"backlog_reduction": 0.3231552163, "backlog_reduction_utility": 0.4810606061, "backlog_unit_weeks": 266, "capacity_utilization": 0.8543371522, "demand_units": 471, "ending_backlog": 43, "inventory_instability": 0.4919655584, "inventory_stability": 0.6702567592, "inventory_stability_utility": 0.8589110898, "operational_risk": 0.3994010049, "operational_risk_utility": 0.0, "otif": 0.5817409766, "otif_utility": 0.1597633136, "overload_weeks": 10, "plan_adherence": 0.8868778281, "produced": 428, "rank": 4, "recovery_cost": 2592000.0, "recovery_cost_utility": 0.3576208178, "scenario": 1, "stockout_component_weeks": 15, "wape": 0.0858195329, "weighted_score": 0.3685549726}`
- [scenario_metrics:0](csv/scenario_metrics.csv): `{"backlog_unit_weeks": 393, "capacity_utilization": 0.8543371522, "demand_units": 471, "ending_backlog": 43, "inventory_instability": 0.8463889812, "inventory_stability": 0.5415976862, "operational_risk": 0.2420905746, "otif": 0.5244161359, "overload_weeks": 11, "plan_adherence": 0.9140271493, "produced": 428, "recovery_cost": 0, "scenario": 0, "stockout_component_weeks": 15, "wape": 0.0858195329}`

Full exception coverage and source keys: [evidence package](exception_evidence.json).
Dollar amounts cover modeled incremental recovery costs only; no total lifecycle cost claim.
