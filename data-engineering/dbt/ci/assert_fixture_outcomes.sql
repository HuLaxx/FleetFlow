-- Non-empty fixture outcomes supplement dbt generic/singular tests.
-- A failure here exits psql nonzero, failing CI.
DO $$
DECLARE
  d1 record;
  d2 record;
  dcount integer;
BEGIN
  IF current_database() <> 'fleetflow_test' THEN
    RAISE EXCEPTION 'Refusing KPI checks against a non-test database';
  END IF;
  SELECT * INTO d1 FROM public_marts.fct_daily_performance WHERE date='2026-11-12';
  SELECT * INTO d2 FROM public_marts.fct_daily_performance WHERE date='2026-11-13';
  SELECT COUNT(*) INTO dcount FROM public_marts.dim_driver_performance;
  IF d1 IS NULL OR d2 IS NULL OR dcount <> 1 THEN
    RAISE EXCEPTION 'Expected both dates and exactly one synthetic driver';
  END IF;
  IF d1.total_orders <> 2 OR d1.delivered_orders <> 1
     OR d1.total_routes <> 2 OR d1.completed_routes <> 1
     OR d1.delivery_success_rate_pct <> 50.00
     OR d1.total_planned_distance_km <> 32.00
     OR d1.total_actual_distance_km <> 15.00
     OR d1.observed_vs_planned_distance_pct <> 125.00
     OR d1.total_planned_stops <> 3 OR d1.total_completed_stops <> 1
     OR d1.active_drivers <> 1 THEN
     RAISE EXCEPTION 'Date 1 source reconciliation or measured KPIs incorrect';
  END IF;
  IF d2.total_orders <> 0 OR d2.total_routes <> 1 OR d2.completed_routes <> 0
     OR d2.delivery_success_rate_pct IS NOT NULL
     OR d2.total_actual_distance_km IS NOT NULL
     OR d2.observed_vs_planned_distance_pct IS NOT NULL
     OR d2.active_drivers <> 0
     OR d2.orders_per_active_driver IS NOT NULL THEN
     RAISE EXCEPTION 'Route-only day must not invent actuals or rates';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public_marts.dim_driver_performance
    WHERE observed_distance_km <> 15.00 OR observed_duration_minutes <> 55
  ) THEN
    RAISE EXCEPTION 'Observed driver facts do not match fixture';
  END IF;
END
$$;
