import logging
import os
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TraceProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter


from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry._logs import set_logger_provider

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.boto3sqs import Boto3SQSInstrumentor
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

def setup_telemtry(
        service_name: str,
        service_version: str = "1.0.0",
        otlp_endpoint: Optional[str] = None,       
) -> tuple[trace.Tracer, metrics.Meter]:
    endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    trace_provider = TraceProvider(resource=resource)
    
    trace_exporter = OTLPSpanExporter(
        endpoint = endpoint,
        insecure = True,
    )

    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

    trace.set_tracer_provider(trace_provider)

    tracer = trace.get_tracer(service_name, service_version)

    metric_exporter = OTLPMetricExporter(
        endpoint = endpoint,
        insecure = True,
    )

    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis = 60000,
    )

    meter_provider = MeterProvide(resource = resource, metric_readers = [metric_reader])
    metrics.set_meter_provider(meter_provider)

    meter = metrics.get_meter(service_name, service_version)

    log_exporter = OTLPLogExporter(
        endpoint = endpoint,
        insecure = True,
    )

    logger_provider = LoggerProvider(resource = resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    handler = LoggingHandler(level = logging.INFO, logger_provider = logger_provider)

    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    RequestsInstrumentor().instrument()

    RedisInstrumentor().instrument()

    BotocoreInstrumentor().instrument()

    print(f"[OpenTelemetry] Initialized for service: {service_name}")
    print(f"[OpenTelemetry] Sending telemetry to: {endpoint}")

    return tracer, meter

def instrument_fastapi(app):
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls = "health, healthz, ready, readyz",
    )
    
