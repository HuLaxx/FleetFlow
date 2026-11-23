import copy

import pytest

from fleetflow_observability.freshness import (
    check_expectations,
    evaluate,
    freshness_metric_families,
    markdown_summary,
    parse_sources_json,
    threshold_seconds,
)
from fleetflow_observability.metrics import render


@pytest.mark.parametrize(
    "age,expected",
    [
        (0, "pass"),
        (3600, "pass"),  # exactly at warn_after is not stale (dbt uses '>')
        (3601, "warn"),
        (7200, "warn"),  # exactly at error_after is still only warn
        (7201, "error"),
        (-30, "pass"),  # loader clock ahead of DB clock
    ],
)
def test_evaluate_matches_dbt_exclusive_thresholds(age, expected):
    assert evaluate(age, 3600, 7200) == expected


def test_evaluate_with_only_one_threshold():
    assert evaluate(10_000, None, 7200) == "error"
    assert evaluate(10_000, 3600, None) == "warn"
    assert evaluate(10_000, None, None) == "pass"


def test_threshold_seconds():
    assert threshold_seconds({"count": 6, "period": "hour"}) == 21600
    assert threshold_seconds({"count": 2, "period": "day"}) == 172800
    assert threshold_seconds({"count": 30, "period": "minute"}) == 1800
    assert threshold_seconds(None) is None
    assert threshold_seconds({"count": None, "period": None}) is None
    with pytest.raises(ValueError):
        threshold_seconds({"count": 1, "period": "week"})
    with pytest.raises(ValueError):
        threshold_seconds({"count": 0, "period": "hour"})


def test_parse_synthetic_artifact(sources_data):
    report = parse_sources_json(sources_data)
    by_table = report.by_table()
    assert set(by_table) == {"orders", "drivers", "route_stops", "routes"}
    assert by_table["orders"].source == "raw"
    assert by_table["drivers"].age_seconds == 108000
    assert by_table["route_stops"].error_after_seconds == 172800
    assert by_table["routes"].status == "runtime error"
    assert "does not exist" in by_table["routes"].error
    assert report.worst() == "runtime error"
    assert report.counts() == {"pass": 1, "warn": 1, "error": 1, "runtime error": 1}
    assert report.dbt_version == "1.8.8"
    assert report.disagreements() == []


def test_age_derived_when_dbt_omits_it(sources_data):
    data = copy.deepcopy(sources_data)
    del data["results"][0]["max_loaded_at_time_ago_in_s"]
    assert parse_sources_json(data).by_table()["orders"].age_seconds == 3600


def test_disagreement_is_detected(sources_data):
    data = copy.deepcopy(sources_data)
    data["results"][2]["status"] = "pass"  # 50h old with 48h error_after
    report = parse_sources_json(data)
    assert [r.table for r in report.disagreements()] == ["route_stops"]
    assert any("thresholds imply error" in p for p in check_expectations(report, {}))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("results"),
        lambda d: d["results"][0].update(status="stale"),
        lambda d: d["results"][0].update(unique_id="model.fleetflow.orders"),
    ],
)
def test_invalid_artifacts_rejected(sources_data, mutate):
    data = copy.deepcopy(sources_data)
    mutate(data)
    with pytest.raises(ValueError):
        parse_sources_json(data)


def test_expectations(sources_data):
    report = parse_sources_json(sources_data)
    ok = {"orders": "pass", "drivers": "warn", "route_stops": "error", "routes": "runtime error"}
    assert check_expectations(report, ok) == []
    problems = check_expectations(report, {"orders": "warn", "depots": "pass"})
    assert "orders: expected warn, dbt reported pass" in problems
    assert "depots: expected pass, but no freshness result was produced" in problems
    assert any(p.startswith("drivers: unexpected") for p in problems)


def test_freshness_metrics(sources_data):
    text = render(freshness_metric_families(parse_sources_json(sources_data)))
    assert 'fleetflow_source_freshness_status_code{source="raw",table="route_stops"} 2' in text
    assert 'fleetflow_source_freshness_status_code{source="raw",table="routes"} 3' in text
    assert 'fleetflow_source_freshness_age_seconds{source="raw",table="drivers"} 108000' in text
    assert 'fleetflow_source_freshness_sources{status="warn"} 1' in text
    # generated_at 2026-11-23T12:00:05Z
    assert "fleetflow_source_freshness_check_timestamp_seconds 1795435205" in text
    # runtime error has no age sample
    assert 'age_seconds{source="raw",table="routes"}' not in text


def test_markdown_summary(sources_data):
    md = markdown_summary(parse_sources_json(sources_data))
    assert "| `raw.route_stops` | error | error | 2 days, 2:00:00 | 1 day, 0:00:00 | 2 days, 0:00:00 |" in md
    assert "Worst: **runtime error**" in md
