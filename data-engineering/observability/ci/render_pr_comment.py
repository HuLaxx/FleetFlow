"""Build the PR comment for .github/workflows/observability.yml.

Usage: python render_pr_comment.py ARTIFACT_DIR NEEDS_JSON RUN_URL SHA > comment.md
Failed jobs get the tail of their logs so the result is readable without
access to the Actions log viewer.
"""

import json
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - parsing our own CI output
from pathlib import Path

TAIL = 80


def tail(path, n=TAIL):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


def junit_summary(path):
    if not path.exists():
        return None
    root = ET.parse(path).getroot()  # noqa: S314
    suites = [root] if root.tag == "testsuite" else list(root)
    total = {k: sum(int(s.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    passed = total["tests"] - total["failures"] - total["errors"] - total["skipped"]
    return f"{passed} passed, {total['failures']} failed, {total['errors']} errors, {total['skipped']} skipped"


def coverage_total(path):
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if line.startswith("TOTAL"):
            return line.split()[-1]
    return None


def main():
    art, needs, run_url, sha = Path(sys.argv[1]), json.loads(sys.argv[2]), sys.argv[3], sys.argv[4]
    ok = all(v.get("result") == "success" for v in needs.values())
    out = [
        "## FleetFlow observability CI " + ("✅ passed" if ok else "❌ failed"),
        "",
        f"Commit `{sha[:7]}` · [workflow run]({run_url}) · data in these checks is **synthetic**.",
        "",
        "| Job | Result |",
        "| --- | --- |",
    ]
    out += [f"| `{job}` | {info.get('result')} |" for job, info in needs.items()]

    unit = art / "unit"
    tests, cov = junit_summary(unit / "junit.xml"), coverage_total(unit / "coverage.txt")
    if tests:
        out += ["", f"**Unit tests:** {tests}" + (f" · line+branch coverage **{cov}**" if cov else "")]

    e2e = art / "e2e" / "out"
    for stage in ("stale", "healthy"):
        md = e2e / stage / "summary.md"
        if md.exists():
            out += ["", f"<details><summary>dbt source freshness — {stage} scenario</summary>", "", md.read_text()]
            out += ["</details>"]
    for name in ("prom-stale", "prom-healthy"):
        rep = e2e / f"{name}.json"
        if rep.exists():
            data = json.loads(rep.read_text())
            verdict = "met" if data["ok"] else "UNMET: " + "; ".join(data["failures"])
            alerts = data["alerts"] or ["(no active alerts)"]
            out += ["", f"**Prometheus {name.split('-')[1]} alerts:** {verdict}", "```", *alerts, "```"]
    hooks = e2e / "webhook.jsonl"
    if hooks.exists():
        titles = [json.loads(line)["alert"]["title"] for line in hooks.read_text().splitlines() if line.strip()]
        out += ["", f"**Webhook alerts received ({len(titles)}):** " + "; ".join(titles)]

    for job, info in needs.items():
        if info.get("result") == "success":
            continue
        logs = sorted((art / job / "logs").glob("*.log")) if (art / job / "logs").exists() else []
        out += ["", f"### `{job}` logs (last {TAIL} lines per step)"]
        if not logs:
            out += ["_No logs were uploaded for this job (it may have failed before the first step)._"]
        for log in logs:
            out += [f"<details open><summary>{log.name}</summary>", "", "```", tail(log), "```", "</details>"]
    print("\n".join(out))


if __name__ == "__main__":
    main()
