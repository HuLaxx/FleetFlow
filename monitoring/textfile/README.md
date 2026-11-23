node_exporter's textfile collector reads `*.prom` files from this directory
(mounted read-only by `monitoring/docker-compose.yml`). Pipelines write them with
`python -m fleetflow_observability ... --metrics-out monitoring/textfile/<name>.prom`.
Generated `*.prom` files are git-ignored.
