import logging
from datetime import datetime, timedelta, timezone

import pytest

from fleetflow_observability.alerts import (
    Alert,
    AlertDispatcher,
    Deduplicator,
    LogSink,
    WebhookSink,
    alert_for_run,
    alerts_for_freshness,
    dispatcher_from_env,
)
from fleetflow_observability.freshness import parse_sources_json
from fleetflow_observability.runs import PipelineRun

T0 = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)
ALERT = Alert("critical", "Pipeline failed: p.t", "boom", "run-failed:p:t", {"pipeline": "p"})


def no_sleep(_):
    pass


def test_payload_is_slack_compatible():
    payload = ALERT.to_payload()
    assert payload["text"] == "[CRITICAL] Pipeline failed: p.t: boom"
    assert payload["alert"]["labels"] == {"pipeline": "p"}
    with pytest.raises(ValueError):
        Alert("page-everyone", "t", "s", "k")


def test_webhook_delivers_json(webhook_receiver):
    with webhook_receiver() as rx:
        assert WebhookSink(rx.url, sleep=no_sleep).send(ALERT) is True
    [req] = rx.requests
    assert req["path"] == "/hook"
    assert req["headers"]["Content-Type"] == "application/json"
    assert req["json"]["alert"]["dedup_key"] == "run-failed:p:t"


def test_webhook_retries_5xx_then_succeeds(webhook_receiver):
    with webhook_receiver([503, 500, 200]) as rx:
        sink = WebhookSink(rx.url, retries=3, sleep=no_sleep)
        assert sink.send(ALERT) is True
    assert sink.attempts == 3 and len(rx.requests) == 3


def test_webhook_does_not_retry_4xx(webhook_receiver):
    with webhook_receiver([400, 200]) as rx:
        sink = WebhookSink(rx.url, retries=3, sleep=no_sleep)
        assert sink.send(ALERT) is False
    assert sink.attempts == 1


def test_webhook_retries_429(webhook_receiver):
    with webhook_receiver([429, 200]) as rx:
        assert WebhookSink(rx.url, retries=2, sleep=no_sleep).send(ALERT) is True


def test_webhook_unreachable_returns_false_with_backoff():
    sleeps = []
    sink = WebhookSink("http://127.0.0.1:9/hook", timeout=0.5, retries=3, backoff_seconds=0.1, sleep=sleeps.append)
    assert sink.send(ALERT) is False
    assert sleeps == [0.1, 0.2]


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x/y", "not a url", "https://"])
def test_webhook_rejects_non_http_urls(url):
    with pytest.raises(ValueError):
        WebhookSink(url)


def test_deduplicator_window(tmp_path):
    now = [1000.0]
    dedup = Deduplicator(tmp_path / "state.json", timedelta(minutes=10), clock=lambda: now[0])
    assert dedup.should_send("k")
    dedup.mark_sent("k")
    now[0] += 599
    assert not dedup.should_send("k")
    now[0] += 1
    assert dedup.should_send("k")


def test_deduplicator_survives_corrupt_state(tmp_path, caplog):
    path = tmp_path / "state.json"
    path.write_text("{oops")
    dedup = Deduplicator(path, timedelta(minutes=1))
    assert dedup.should_send("k")
    dedup.mark_sent("k")
    assert not dedup.should_send("k")


class Boom:
    name = "boom"

    def send(self, alert):
        raise RuntimeError("sink broke")


class Down:
    name = "down"

    def send(self, alert):
        return False


def test_dispatcher_isolates_sink_failures(tmp_path):
    sent = []

    class Ok:
        name = "ok"

        def send(self, alert):
            sent.append(alert)
            return True

    dedup = Deduplicator(tmp_path / "s.json", timedelta(hours=1))
    d = AlertDispatcher([Boom(), Ok()], dedup)
    first = d.dispatch([ALERT])
    second = d.dispatch([ALERT])
    assert first.sent == ["run-failed:p:t"] and second.suppressed == ["run-failed:p:t"]
    assert len(sent) == 1


def test_dispatcher_reports_undelivered_and_does_not_mark_sent(tmp_path):
    dedup = Deduplicator(tmp_path / "s.json", timedelta(hours=1))
    report = AlertDispatcher([Down()], dedup).dispatch([ALERT])
    assert report.failed == ["run-failed:p:t"]
    assert dedup.should_send("run-failed:p:t")  # will retry next time
    with pytest.raises(ValueError):
        AlertDispatcher([])


def test_dispatcher_from_env(tmp_path, webhook_receiver, caplog):
    assert [s.name for s in dispatcher_from_env({}).sinks] == ["log"]
    with webhook_receiver() as rx:
        d = dispatcher_from_env(
            {
                "FLEETFLOW_ALERT_WEBHOOK_URL": rx.url,
                "FLEETFLOW_ALERT_DEDUP_STATE": str(tmp_path / "d.json"),
                "FLEETFLOW_ALERT_DEDUP_MINUTES": "5",
            }
        )
        assert [s.name for s in d.sinks] == ["webhook", "log"]
        with caplog.at_level(logging.WARNING):
            d.dispatch([ALERT, ALERT])
    assert len(rx.requests) == 1  # second one deduplicated
    assert "ALERT" in caplog.text


def test_log_sink_levels(caplog):
    with caplog.at_level(logging.WARNING):
        LogSink().send(ALERT)
        LogSink().send(Alert("warning", "t", "s", "k2"))
    levels = [r.levelname for r in caplog.records]
    assert levels == ["ERROR", "WARNING"]


def test_alert_for_run():
    r = PipelineRun(pipeline="p", task="t", started_at=T0, error_type="KeyError", error_message="'x'", attempt=2)
    r.finish("failed", T0 + timedelta(seconds=2.5))
    alert = alert_for_run(r)
    assert alert.summary == "KeyError: 'x' (attempt 2, ran 2.5s)"
    assert alert.labels["run_id"] == r.run_id
    ok = PipelineRun(pipeline="p", task="t", started_at=T0).finish("success", T0)
    with pytest.raises(ValueError):
        alert_for_run(ok)


def test_alerts_for_freshness(sources_data):
    report = parse_sources_json(sources_data)
    alerts = {a.labels["table"]: a for a in alerts_for_freshness(report.results)}
    assert set(alerts) == {"drivers", "route_stops", "routes"}
    assert alerts["drivers"].severity == "warning"
    assert alerts["route_stops"].severity == "critical"
    assert alerts["route_stops"].summary == "last load 2 days, 2:00:00 ago exceeds error threshold 2 days, 0:00:00"
    assert "could not run" in alerts["routes"].summary
    only_errors = alerts_for_freshness(report.results, "error")
    assert {a.labels["table"] for a in only_errors} == {"route_stops", "routes"}
