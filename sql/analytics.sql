-- Shared grain: scenario × week × product. Do not join FAL totals to products then sum them.
CREATE VIEW weekly_kpi AS
WITH totals AS (
  SELECT scenario, week, SUM(demand_units) AS demand_units, SUM(produced) AS produced,
         SUM(on_time_due) AS on_time_due, SUM(backlog) AS backlog,
         SUM(baseline_plan) AS baseline_plan, SUM(absolute_deviation) AS absolute_deviation
  FROM production_plan GROUP BY scenario, week
), rolling AS (
  SELECT *, SUM(on_time_due) OVER w AS rolling_on_time,
            SUM(demand_units) OVER w AS rolling_demand,
            LAG(backlog, 1, 0) OVER (PARTITION BY scenario ORDER BY week) AS previous_backlog
  FROM totals
  WINDOW w AS (PARTITION BY scenario ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)
)
SELECT r.*, 1.0*r.on_time_due/NULLIF(r.demand_units,0) AS otif,
       1.0*r.rolling_on_time/NULLIF(r.rolling_demand,0) AS rolling_4w_otif,
       r.backlog-r.previous_backlog AS backlog_change,
       c.used_hours, c.available_hours, c.overload_hours,
       c.used_hours/NULLIF(c.available_hours,0) AS capacity_utilization,
       MAX(0.0, 1.0-1.0*r.absolute_deviation/NULLIF(r.baseline_plan,0)) AS plan_adherence
FROM rolling r JOIN capacity_execution c USING(scenario,week);

CREATE VIEW forecast_accuracy AS
WITH actual AS (
 SELECT scenario, week, product, demand_units FROM production_plan
), fixed_forecast AS (
 SELECT week, product, forecast_units FROM demand_forecast WHERE vintage_week=1
)
SELECT a.scenario, a.week, a.product, a.demand_units, f.forecast_units,
       ABS(a.demand_units-f.forecast_units) AS absolute_error,
       1.0*SUM(ABS(a.demand_units-f.forecast_units)) OVER (
          PARTITION BY a.scenario,a.product ORDER BY a.week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)
       /NULLIF(SUM(a.demand_units) OVER (
          PARTITION BY a.scenario,a.product ORDER BY a.week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW),0) AS rolling_4w_wape
FROM actual a JOIN fixed_forecast f USING(week,product);

CREATE VIEW order_risk AS
SELECT scenario, order_id, product, due_week, delivery_week, priority, delay_weeks,
       CASE WHEN delivery_week IS NULL THEN 'Open at horizon'
            WHEN on_time=0 THEN 'Delivered late' ELSE 'On time' END AS status,
       ROW_NUMBER() OVER (PARTITION BY scenario ORDER BY
          CASE WHEN delivery_week IS NULL THEN 0 ELSE 1 END, priority, due_week, order_id) AS review_sequence
FROM order_fulfillment WHERE late_or_open=1;

CREATE VIEW constraint_exceptions AS
SELECT scenario, week, 'FAL demand overload' AS exception_type, 'FAL' AS resource,
       overload_hours AS magnitude, 'hours' AS unit
FROM capacity_execution WHERE overload_hours>0
UNION ALL
SELECT scenario, week, 'Material blocking', component, blocked_orders, 'order-week events'
FROM material_balance WHERE blocked_orders>0;

CREATE VIEW supplier_release_load AS
SELECT scenario, supplier, component, release_week,
       SUM(units) AS allocated_units, MAX(available_capacity) AS available_capacity,
       MAX(master_capacity) AS master_capacity,
       1.0*SUM(units)/NULLIF(MAX(available_capacity),0) AS release_utilization,
       SUM(incremental_cost) AS incremental_cost
FROM supply_shipments GROUP BY scenario,supplier,component,release_week;

CREATE VIEW component_risk_rank AS
WITH counts AS (
 SELECT scenario,component,SUM(blocked_orders) AS blocked_order_weeks,
        SUM(stockout) AS stockout_weeks,AVG(coverage_weeks) AS average_coverage
 FROM material_balance GROUP BY scenario,component
)
SELECT *, DENSE_RANK() OVER (PARTITION BY scenario ORDER BY blocked_order_weeks DESC) AS risk_rank
FROM counts;
