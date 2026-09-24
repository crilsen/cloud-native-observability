import asyncio
import json
import logging
import os
import random

from fastapi import FastAPI, Query
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider

SERVICE_NAME, OTLP_ENDPOINT = "payment-api", os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317")
class JsonFormatter(logging.Formatter):
    def format(self, record):
        ctx = trace.get_current_span().get_span_context()
        return json.dumps({"level": record.levelname, "service": SERVICE_NAME, "message": record.getMessage(), "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else "", "span_id": format(ctx.span_id, "016x") if ctx.is_valid else ""})
def setup():
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource); provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True))); set_tracer_provider(provider)
    from opentelemetry.metrics import set_meter_provider
    set_meter_provider(MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True))]))
    logs = LoggerProvider(resource=resource); logs.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTLP_ENDPOINT, insecure=True))); set_logger_provider(logs)
    root = logging.getLogger(); root.setLevel(logging.INFO); stream = logging.StreamHandler(); stream.setFormatter(JsonFormatter()); root.addHandler(stream); root.addHandler(LoggingHandler(logger_provider=logs))
setup(); app = FastAPI(title=SERVICE_NAME); FastAPIInstrumentor.instrument_app(app); logger = logging.getLogger(SERVICE_NAME)
@app.get("/health")
async def health(): return {"status": "ok"}
@app.get("/payment/process")
async def process_payment(slow: bool = Query(False)):
    delay = random.uniform(1.0, 2.0) if slow else (random.uniform(0.8, 1.5) if random.random() < 0.2 else random.uniform(0.05, 0.15))
    logger.info("processing payment with %.3fs delay", delay)
    await asyncio.sleep(delay)
    logger.info("payment approved")
    return {"payment": "approved", "latency_ms": round(delay * 1000)}
