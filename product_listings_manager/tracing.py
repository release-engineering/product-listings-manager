# SPDX-License-Identifier: GPL-2.0+
import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def init_tracing(app):
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    service_name = os.getenv("OTEL_EXPORTER_SERVICE_NAME")
    if not endpoint or not service_name:
        logger.warning("Trancing not initialized")
        return

    logger.info("Initializing tracing: %s", endpoint)

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    trace.set_tracer_provider(provider)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))

    FastAPIInstrumentor().instrument_app(app, tracer_provider=provider)
