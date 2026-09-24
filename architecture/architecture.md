# MVP Architecture

The applications are instrumented only against OpenTelemetry APIs and export OTLP to the Collector. Backend-specific configuration is isolated from application code.

```mermaid
flowchart LR
  Client --> Frontend[frontend-api]
  Frontend --> Orders[orders-api]
  Orders --> Payment[payment-api]
  Frontend & Orders & Payment -->|OTLP| Collector[OpenTelemetry Collector]
  Collector --> Prometheus
  Collector --> Tempo
  Collector --> Loki
  Prometheus & Tempo & Loki --> Grafana
```

The Docker Compose deployment is deliberately local-only. It introduces no Kubernetes or cloud dependencies; a later port can preserve the OTLP boundary while replacing the runtime platform.
