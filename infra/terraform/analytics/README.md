# FleetFlow P3 — optional, cost-aware AWS analytics sandbox

**Status:** Terraform configuration in draft PR only. No `terraform apply`,
`terraform plan`, AWS credentials, live deployment, streaming ingestion or
cloud billing evidence. The review CI performs `fmt`, provider initialization
without remote state and `validate` **only**.

## What this module would create *after separate human approval*

| Resource | Function | Cost/safety control |
|---|---|---|
| Private S3 bucket | Optional `raw/`, `clean/`, `curated/`, `athena-results/` Parquet and results | Public ACL/policy blocks, TLS deny, SSE-S3, versioning, `force_destroy=false` |
| Glue Catalog database | Metadata namespace | Does not create crawlers, tables or ETL jobs |
| Athena workgroup | Optional SQL over human-registered lake data | SSE-S3 query results, **1 GiB per-query** bytes scanned cutoff; not a monthly cap |
| GitHub OIDC review role | Small-scale ingestion/query access only | Restricted to exact `repo:HuLaxx/FleetFlow:environment:analytics-review`; provider ARN passed by user; no administrative/terraform permissions |

**Not included:** Lambda, EventBridge, ECS, live Kafka-to-S3 uploader,
API hosting, public UI, CloudWatch custom alarm thresholds, automatic
retention, secret storage or an account budget. These are design/deployment
gates that require separate workload evidence and approval, not decorative
resources to create early.

**Terraform state:** This module deliberately specifies **no remote backend**.
Do not apply while using local state for a real account. Configure an
encrypted, restricted remote state backend with locking, obtain reviewed
credentials, and require protected approvals before applying. No workflow
contains `terraform apply` or `destroy`. Versioned S3 storage can retain
older copies and increase bills; agree a retention/deletion policy before use.

## Independent reproducible validation (no account)

```bash
terraform fmt -check -recursive infra/terraform/analytics
terraform -chdir=infra/terraform/analytics init -backend=false -input=false
terraform -chdir=infra/terraform/analytics validate
```

Inputs requiring human authorization: globally unique bucket name, region,
existing GitHub OIDC provider ARN and GitHub protected `analytics-review`
environment. The GitHub role is **not** a Terraform execution role.

## Cost scenario — illustrative, NOT a bill or maximum

For `eu-west-2` (London), suppose 5 GB stored in S3 Standard for one month,
1,000 S3 write operations, 100 small Athena queries charged at the 10 MB
minimum each, and catalog use below its free-tier metadata threshold.

| Meter | Illustrative arithmetic | Indicative charge |
|---|---|---|
| S3 Standard storage | 5 GB × approximately $0.024/GB-month | ~$0.12 |
| S3 PUT-like requests | 1,000 × approximately $0.0053 per 1,000 | ~$0.005 |
| Athena scanned data | 100 × 10 MB minimum ≈ 1 GB × approximately $5/TB | ~$0.005 |
| Glue Data Catalog | Under first million objects/requests, if applicable | ~$0 |

These amounts are **usage assumptions**, not observed measurements or a
guaranteed price. They exclude S3 GET/LIST, versioning growth, any data
transfer, taxes, storage/query requests beyond the example, CloudWatch
metrics, AWS Budgets beyond the free allowance, and other services or
regional pricing differences. Use the AWS Pricing Calculator and set a low
AWS Budget with alerts **before approval**. Budget alerts are **not hard
spending caps**. One GiB **per query** does not bound how many queries run.

Pricing references (verify again at deployment):
- https://aws.amazon.com/s3/pricing/
- https://aws.amazon.com/athena/pricing/
- https://aws.amazon.com/glue/pricing/

## Exact project evidence and honest limitations

P1 synthetic GPS browser → Redpanda → PostGIS was verified in PR #9.
P2 immutable replay, reconciled clean/curated Parquet, PostgreSQL import and
actual dbt SQL were verified in draft PRs #14/#15. The AWS resources above are
currently **only Terraform definitions**. There is no authenticated cloud
analytics deployment, S3-import smoke test, AWS performance benchmark or
production invoice. No GitHub repo branch is merged by this document.
