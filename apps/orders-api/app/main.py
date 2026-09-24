import asyncio
import json
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException, Query
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler, set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import RESOURCE_ATTRIBUTES, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider

SERVICE_NAME, OTLP_ENDPOINT = "orders-api", os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317")
PAYMENT_URL = os.getenv("PAYMENT_API_URL", "http://payment-api:8002")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        ctx = trace.get_current_span().get_span_context()
        return json.dumps({"level": record.levelname, "service": SERVICE_NAME, "message": record.getMessage(), "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else "", "span_id": format(ctx.span_id, "016x") if ctx.is_valid else ""})

def setup():
    resource = Resource.create({RESOURCE_ATTRIBUTES.SERVICE_NAME: SERVICE_NAME})
    provider = TracerProvider(resource=resource); provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True))); set_tracer_provider(provider)
    from opentelemetry.metrics import set_meter_provider
    set_meter_provider(MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True))]))
    logs = LoggerProvider(resource=resource); logs.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTLP_ENDPOINT, insecure=True))); set_logger_provider(logs)
    root = logging.getLogger(); root.setLevel(logging.INFO); stream = logging.StreamHandler(); stream.setFormatter(JsonFormatter()); root.addHandler(stream); root.addHandler(LoggingHandler(logger_provider=logs)); HTTPXClientInstrumentor().instrument()

setup(); app = FastAPI(title=SERVICE_NAME); FastAPIInstrumentor.instrument_app(app); logger = logging.getLogger(SERVICE_NAME)

@app.get("/health")
async def health(): return {"status": "ok"}

@app.get("/orders/process")
async def process_order(slow: bool = Query(False)):
    logger.info("processing order")
    await asyncio.sleep(0.1)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PAYMENT_URL}/payment/process", params={"slow": str(slow).lower()})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("payment processing failed")
        raise HTTPException(status_code=502, detail="payment service unavailable") from exc
    logger.info("order processed")
    return {"order": "processed", "payment": response.json()}
