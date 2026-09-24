# Architecture

`frontend-api /checkout` calls `orders-api /orders/process`, which calls `payment-api /payment/process`.

All applications export OTLP/gRPC to the OpenTelemetry Collector. Its separate pipelines forward traces to Tempo, expose metrics for Prometheus scraping, and forward logs through OTLP/HTTP to Loki. Grafana is provisioned with all three datasources.

The application-to-Collector OTLP boundary keeps backend dependencies out of application code. See `architecture/architecture.md` for the diagram.
