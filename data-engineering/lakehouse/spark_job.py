"""PySpark job: validated bronze CSV -> silver Parquet (conformed, enriched, partitioned).

Runs locally (``local[*]``), on Databricks (Free Edition / serverless) or any
Spark 3.5 cluster. Paths can be local folders, ``dbfs:/``, ``abfss://`` (ADLS Gen2)
or ``s3a://`` URIs.

Idempotency and backfills
-------------------------
The delivery fact is written partitioned by ``delivery_date`` with
``spark.sql.sources.partitionOverwriteMode=dynamic``. Re-running the job for a
date range rewrites only those partitions, so re-runs and backfills never
duplicate rows. Dimensions are small and fully overwritten on every run.

Usage:
    python -m lakehouse.spark_job --root data/lakehouse --start-date 2026-01-01 --end-date 2026-01-30
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

SCHEMAS = {
    "depots": T.StructType([
        T.StructField("depot_id", T.StringType(), False),
        T.StructField("depot_name", T.StringType()),
        T.StructField("city", T.StringType()),
        T.StructField("latitude", T.DoubleType()),
        T.StructField("longitude", T.DoubleType()),
    ]),
    "vehicles": T.StructType([
        T.StructField("vehicle_id", T.StringType(), False),
        T.StructField("depot_id", T.StringType()),
        T.StructField("vehicle_type", T.StringType()),
        T.StructField("capacity_kg", T.IntegerType()),
    ]),
    "drivers": T.StructType([
        T.StructField("driver_id", T.StringType(), False),
        T.StructField("employee_id", T.StringType()),
        T.StructField("depot_id", T.StringType()),
        T.StructField("hired_date", T.DateType()),
        T.StructField("rating", T.DoubleType()),
    ]),
    "customers": T.StructType([
        T.StructField("customer_id", T.StringType(), False),
        T.StructField("city", T.StringType()),
        T.StructField("segment", T.StringType()),
    ]),
    "orders": T.StructType([
        T.StructField("order_id", T.StringType(), False),
        T.StructField("order_number", T.StringType()),
        T.StructField("customer_id", T.StringType()),
        T.StructField("depot_id", T.StringType()),
        T.StructField("delivery_date", T.DateType()),
        T.StructField("window_start", T.TimestampType()),
        T.StructField("window_end", T.TimestampType()),
        T.StructField("weight_kg", T.DoubleType()),
        T.StructField("value_gbp", T.DoubleType()),
        T.StructField("priority", T.IntegerType()),
        T.StructField("created_at", T.TimestampType()),
    ]),
    "deliveries": T.StructType([
        T.StructField("event_id", T.StringType(), False),
        T.StructField("order_id", T.StringType()),
        T.StructField("vehicle_id", T.StringType()),
        T.StructField("driver_id", T.StringType()),
        T.StructField("attempted_at", T.TimestampType()),
        T.StructField("status", T.StringType()),
        T.StructField("distance_km", T.DoubleType()),
        T.StructField("ingested_at", T.TimestampType()),
    ]),
}
DIMENSIONS = ["depots", "vehicles", "drivers", "customers"]
ON_TIME_GRACE_MINUTES = 15


def build_spark(app: str = "fleetflow-silver") -> SparkSession:
    return (SparkSession.builder.appName(app)
            .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.shuffle.partitions", "8")
            .getOrCreate())


def read_table(spark: SparkSession, root: str, name: str) -> DataFrame:
    # FAILFAST: a row that doesn't match the contract schema stops the job instead of becoming nulls.
    return (spark.read.option("header", True).option("mode", "FAILFAST")
            .option("timestampFormat", "yyyy-MM-dd HH:mm:ss")
            .schema(SCHEMAS[name]).csv(f"{root}/validated/{name}"))


def build_delivery_fact(orders: DataFrame, deliveries: DataFrame) -> DataFrame:
    latest = (deliveries
              .withColumn("_rn", F.row_number().over(
                  Window.partitionBy("event_id").orderBy(F.col("ingested_at").desc())))
              .filter("_rn = 1").drop("_rn"))
    fact = (latest.join(orders, "order_id", "inner")
            .withColumn("lateness_minutes",
                        F.round((F.col("attempted_at").cast("long") - F.col("window_end").cast("long")) / 60.0, 1))
            .withColumn("is_on_time",
                        (F.col("status") == "delivered") & (F.col("lateness_minutes") <= ON_TIME_GRACE_MINUTES))
            .withColumn("is_delivered", F.col("status") == "delivered")
            .withColumn("ingest_latency_minutes",
                        F.round((F.col("ingested_at").cast("long") - F.col("attempted_at").cast("long")) / 60.0, 1))
            .withColumn("processed_at", F.current_timestamp()))
    return fact.select(
        "event_id", "order_id", "order_number", "customer_id", "depot_id", "vehicle_id", "driver_id",
        "delivery_date", "window_start", "window_end", "attempted_at", "ingested_at", "status",
        "is_delivered", "is_on_time", "lateness_minutes", "ingest_latency_minutes",
        "weight_kg", "value_gbp", "priority", "distance_km", "processed_at",
    )


def run(root: str, start_date: str, end_date: str, spark: SparkSession | None = None) -> dict:
    t0 = time.perf_counter()
    spark = spark or build_spark()
    silver = f"{root}/silver"
    counts: dict[str, int] = {}

    for name in DIMENSIONS:
        df = read_table(spark, root, name).dropDuplicates([SCHEMAS[name].fields[0].name])
        df.write.mode("overwrite").parquet(f"{silver}/{name}")
        counts[name] = df.count()

    orders = (read_table(spark, root, "orders")
              .filter(F.col("delivery_date").between(F.lit(start_date).cast("date"), F.lit(end_date).cast("date"))))
    deliveries = read_table(spark, root, "deliveries")
    fact = build_delivery_fact(orders, deliveries).cache()
    counts["deliveries_in_range"] = fact.count()

    (fact.repartition("delivery_date").write.mode("overwrite")
         .partitionBy("delivery_date").parquet(f"{silver}/deliveries"))

    written = spark.read.parquet(f"{silver}/deliveries")
    counts["deliveries_total_in_silver"] = written.count()
    dup_keys = written.groupBy("event_id").count().filter("count > 1").count()

    seconds = time.perf_counter() - t0
    result = {
        "start_date": start_date, "end_date": end_date, "rows": counts,
        "duplicate_event_ids_in_silver": dup_keys,
        "seconds": round(seconds, 2),
        "fact_rows_per_second": round(counts["deliveries_in_range"] / seconds, 1),
        "spark_version": spark.version,
    }
    if not str(root).startswith(("dbfs:", "abfss:", "s3a:")):
        Path(root, "spark_run_summary.json").write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", default="data/lakehouse")
    p.add_argument("--start-date", required=True)
    p.add_argument("--end-date", required=True)
    a = p.parse_args()
    print(json.dumps(run(a.root, a.start_date, a.end_date), indent=2))


if __name__ == "__main__":
    main()
