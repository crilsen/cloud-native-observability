import asyncio
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

SERVICE_NAME = "frontend-api"
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317")
ORDERS_URL = os.getenv("ORDERS_API_URL", "http://orders-api:8001")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        context = trace.get_current_span().get_span_context()
        return (
            '{"level":"%s","service":"%s","message":%s,"trace_id":"%s","span_id":"%s"}'
            % (record.levelname, SERVICE_NAME, __import__("json").dumps(record.getMessage()),
               format(context.trace_id, "032x") if context.is_valid else "",
               format(context.span_id, "016x") if context.is_valid else "")
        )


def configure_observability() -> None:
    resource = Resource.create({RESOURCE_ATTRIBUTES.SERVICE_NAME: SERVICE_NAME})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)))
    set_tracer_provider(tracer_provider)
    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True))
    from opentelemetry.metrics import set_meter_provider
    set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=OTLP_ENDPOINT, insecure=True)))
    set_logger_provider(logger_provider)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    stream = logging.StreamHandler()
    stream.setFormatter(JsonFormatter())
    root.addHandler(stream)
    root.addHandler(LoggingHandler(logger_provider=logger_provider))
    HTTPXClientInstrumentor().instrument()


configure_observability()
app = FastAPI(title=SERVICE_NAME)
FastAPIInstrumentor.instrument_app(app)
logger = logging.getLogger(SERVICE_NAME)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/checkout")
async def checkout(slow: bool = Query(False)) -> dict:
    logger.info("checkout started")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ORDERS_URL}/orders/process", params={"slow": str(slow).lower()})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("checkout failed")
        raise HTTPException(status_code=502, detail="orders service unavailable") from exc
    logger.info("checkout completed")
    return {"checkout": "completed", "order": response.json()}
