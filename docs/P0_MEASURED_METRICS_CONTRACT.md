# P0 honest operational analytics contract

FleetFlow previously returned hard-coded `on_time_rate=0.96`, `avg_delivery_time_minutes=22`, and `avg_utilization_rate=0.78` without any supporting delivered-order or usage-history query. It also returned numeric zero for several unmeasured totals, which misleadingly suggests the system observed zero activity. The API now emits **JSON `null`** for unmeasured KPIs and preserves real observed counts and statuses; the same contract is enforced by PostGIS-backed tests. A missing or incomplete telemetry source is not a business performance measurement.

These fields remain documented and nullable until we have an approved delivery lifecycle, measured driver operating-hour denominator, complete timestamped GPS history and a trustworthy cost basis. Do not advertise 96% on-time performance or 78% utilisation from the demo; neither is a measured result. Frontend metric cards must display "not available" when they receive `null`, not coerce the value to zero or show a green success badge.

Exact CI head must be green before describing this as verified. No production database, user data, API, or AWS account was touched.
