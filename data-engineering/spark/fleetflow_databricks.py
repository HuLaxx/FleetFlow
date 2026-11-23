# Databricks notebook source
# FleetFlow: real PySpark batch over content-addressed clean Parquet.
# Import this folder as a Databricks Git folder alongside fleetflow_batch.py.
# No input fixture is silently generated or cloud resources provisioned.

# COMMAND ----------
from pathlib import Path
from pyspark.sql import functions as F

from fleetflow_batch import hourly_vehicle_facts, verified_clean_parquet

dbutils.widgets.text("manifest_path", "")
dbutils.widgets.text("output_table", "")
dbutils.widgets.dropdown("publish", "no", ["no", "yes"])

manifest_path = dbutils.widgets.get("manifest_path").strip()
output_table = dbutils.widgets.get("output_table").strip()
publish = dbutils.widgets.get("publish") == "yes"

if not manifest_path.startswith("/Volumes/"):
    raise ValueError("Supply an original replay manifest in a Unity Catalog Volume")

# Manifest, raw bytes, clean Parquet and checksums must be in the SAME
# uploaded run directory. Verify every artifact before reading any data.
manifest, clean_paths = verified_clean_parquet(Path(manifest_path))
spark.conf.set("spark.sql.session.timeZone", "UTC")
source = spark.read.parquet(*clean_paths)
expected = manifest.get("counts")
if not isinstance(expected, dict):
    raise ValueError("manifest counts missing")
if source.count() != expected.get("accepted"):
    raise ValueError("accepted Spark events do not reconcile with replay")
actual_late = source.agg(F.sum(F.col("is_late").cast("long"))).first()[0] or 0
if actual_late != expected.get("late"):
    raise ValueError("late Spark events do not reconcile with replay")
facts = hourly_vehicle_facts(source, manifest["run_key"])
if (facts.agg(F.sum("event_count")).first()[0] or 0) != expected["accepted"]:
    raise ValueError("Spark hourly facts do not reconcile with accepted source")

# COMMAND ----------
display(facts.orderBy("vehicle_id", "hour_utc"))
print({"run_key": manifest["run_key"], "hourly_rows": facts.count(),
       "mode": "publish" if publish else "preview", "manifest_verified": True})

# COMMAND ----------
if publish:
    if not output_table or len(output_table.split(".")) != 3:
        raise ValueError("Provide catalog.schema.table in your own UC workspace")
    if spark.catalog.tableExists(output_table):
        raise ValueError("Target Delta table exists; refusing to overwrite")
    facts.write.format("delta").mode("errorifexists").saveAsTable(output_table)
    print("Published Delta table:", output_table)
