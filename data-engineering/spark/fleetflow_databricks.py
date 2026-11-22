# Databricks notebook source
# FleetFlow: real PySpark batch over immutable, validated local replay Parquet.
# Import this folder as a Databricks Git folder; this notebook and the module
# fleetflow_batch.py must stay side-by-side. No sample data is silently injected.

# COMMAND ----------
import json
from pathlib import Path

from fleetflow_batch import hourly_vehicle_facts

dbutils.widgets.text("manifest_path", "")
dbutils.widgets.text("clean_parquet_path", "")
dbutils.widgets.text("output_table", "")
dbutils.widgets.dropdown("publish", "no", ["no", "yes"])

manifest_path = dbutils.widgets.get("manifest_path").strip()
clean_path = dbutils.widgets.get("clean_parquet_path").strip()
output_table = dbutils.widgets.get("output_table").strip()
publish = dbutils.widgets.get("publish") == "yes"

if not manifest_path or not clean_path:
    raise ValueError("Supply actual manifest_path and clean_parquet_path from the SAME replay run")
if not manifest_path.startswith("/Volumes/") or not clean_path.startswith("/Volumes/"):
    raise ValueError("Use a Unity Catalog volume path in Databricks Free Edition")

# The manifest is copied to the UC Volume alongside the clean Parquet.
manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
run_key = manifest["run_key"]
if not isinstance(run_key, str):
    raise ValueError("Missing manifest run_key")
spark.conf.set("spark.sql.session.timeZone", "UTC")
source = spark.read.parquet(clean_path)
facts = hourly_vehicle_facts(source, run_key)

# COMMAND ----------
display(facts.orderBy("vehicle_id", "hour_utc"))
print({"run_key": run_key, "hourly_rows": facts.count(), "mode": "publish" if publish else "preview"})

# COMMAND ----------
if publish:
    if not output_table or len(output_table.split(".")) != 3:
        raise ValueError("Provide catalog.schema.table to publish in your own UC workspace")
    # Never silently overwrite an existing shared table. Repeated runs must be
    # independently reviewed rather than erasing historical snapshots.
    if spark.catalog.tableExists(output_table):
        raise ValueError("Target table already exists; refusing overwrite")
    facts.write.format("delta").mode("errorifexists").saveAsTable(output_table)
    print("Published Delta table:", output_table)
