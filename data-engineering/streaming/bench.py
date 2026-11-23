"""Throughput benchmark for the GPS stream against a real Kafka broker (synthetic events).

    PYTHONPATH=data-engineering python -m streaming.bench --bootstrap 127.0.0.1:9092 --events 200000
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import uuid
from pathlib import Path

from streaming.gps_structured_stream import count_parquet, run_available_now, spark_session
from streaming.synthetic_gps import gps_event, publish


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", default="127.0.0.1:9092")
    parser.add_argument("--events", type=int, default=200_000)
    parser.add_argument("--output", type=Path, default=Path("stream_bench.json"))
    args = parser.parse_args(argv)
    spark = spark_session("fleetflow-gps-stream-bench")
    topic = f"gps.location.bench.{uuid.uuid4().hex[:8]}"
    events = [gps_event(i, i * 0.001) for i in range(args.events)]
    t0 = time.perf_counter()
    publish(spark, args.bootstrap, topic, events)
    produce_s = time.perf_counter() - t0
    with tempfile.TemporaryDirectory() as tmp:
        t1 = time.perf_counter()
        summary = run_available_now(spark, args.bootstrap, Path(tmp), topic)
        wall_s = time.perf_counter() - t1
        rows = count_parquet(spark, Path(tmp) / "silver")
    report = {
        "scope": "synthetic GPS events, single-node Spark local[2] on a GitHub Actions runner",
        "events": args.events,
        "silver_rows": rows,
        "produce_seconds": round(produce_s, 2),
        "stream_wall_seconds": round(wall_s, 2),
        "end_to_end_events_per_second": round(args.events / wall_s),
        "spark_peak_processed_rows_per_second": round(summary["silver"]["processed_rows_per_second"]),
        "micro_batches": summary["silver"]["batches"],
    }
    args.output.write_text(json.dumps(report, indent=2))
    text = (
        "### GPS Structured Streaming benchmark (synthetic)\n\n"
        f"{report['events']:,} events from Kafka → validated, de-duplicated Parquet in "
        f"{report['stream_wall_seconds']} s: **{report['end_to_end_events_per_second']:,} events/s** "
        f"end to end (Spark peak {report['spark_peak_processed_rows_per_second']:,} rows/s), "
        f"{report['silver_rows']:,} rows written. {report['scope']}.\n"
    )
    print(text)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(text)
    return 0 if rows == args.events else 1


if __name__ == "__main__":
    raise SystemExit(main())
