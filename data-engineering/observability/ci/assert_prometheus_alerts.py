"""Poll a real Prometheus until the expected alert states are reached.

Each expectation is ``STATE:AlertName[,label=value...]`` where STATE is
``firing``, ``pending``, ``active`` (pending or firing) or ``absent``.
Exits 0 when every expectation holds at the same time, 1 on timeout.

Example:
  python assert_prometheus_alerts.py --url http://localhost:9090 \
      --expect firing:FleetflowSourceFreshnessError,table=route_stops \
      --expect absent:FleetflowSourceFreshnessError,table=orders
"""

import argparse
import json
import sys
import time
import urllib.request


def parse(spec):
    state, _, rest = spec.partition(":")
    if state not in ("firing", "pending", "active", "absent") or not rest:
        raise SystemExit(f"bad expectation {spec!r}")
    name, *pairs = rest.split(",")
    labels = dict(p.split("=", 1) for p in pairs)
    return state, name, labels


def matches(alert, name, labels):
    al = alert.get("labels", {})
    return al.get("alertname") == name and all(al.get(k) == v for k, v in labels.items())


def check(alerts, expectations):
    failures = []
    for state, name, labels in expectations:
        hits = [a for a in alerts if matches(a, name, labels)]
        states = {a.get("state") for a in hits}
        ok = {
            "absent": not hits,
            "active": bool(hits),
            "firing": "firing" in states,
            "pending": "pending" in states,
        }[state]
        if not ok:
            failures.append(f"{state}:{name}{labels} (saw states {sorted(states) or 'none'})")
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:9090")
    ap.add_argument("--expect", action="append", required=True)
    ap.add_argument("--timeout", type=float, default=180)
    ap.add_argument("--report", help="write the final alert list + verdict here (JSON)")
    args = ap.parse_args()
    expectations = [parse(s) for s in args.expect]
    deadline = time.time() + args.timeout
    failures, alerts = ["not polled"], []
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{args.url}/api/v1/alerts", timeout=5) as resp:  # noqa: S310
                alerts = json.load(resp)["data"]["alerts"]
        except OSError as exc:
            print(f"prometheus not ready: {exc}")
            time.sleep(3)
            continue
        failures = check(alerts, expectations)
        if not failures:
            break
        time.sleep(3)
    summary = sorted(
        f"{a['state']}: {a['labels'].get('alertname')} "
        + ",".join(f"{k}={v}" for k, v in sorted(a["labels"].items()) if k in ("pipeline", "task", "table"))
        for a in alerts
    )
    print("Active alerts:\n  " + "\n  ".join(summary or ["(none)"]))
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump({"ok": not failures, "failures": failures, "alerts": summary}, fh, indent=2)
    if failures:
        print("UNMET:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print(f"all {len(expectations)} alert expectations met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
