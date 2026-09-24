# Project

## Identity

- **Name:** cloud-native-observability
- **Objective:** A local, portfolio-ready cloud-native observability MVP that correlates distributed traces, metrics and logs across three FastAPI services.
- **Status:** Initial MVP implementation in progress; Docker runtime validation is blocked because the local Docker daemon is unavailable.

## Observed implementation

- Three Python 3.12/FastAPI services are under `apps/`: `frontend-api`, `orders-api`, and `payment-api`.
- `docker-compose.yml` orchestrates those services with an OpenTelemetry Collector, Prometheus, Tempo, Loki, Grafana and an optional k6 load generator.
- The project intentionally excludes Kubernetes, EKS and cloud deployment from this MVP.
