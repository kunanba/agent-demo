"""
OpenTelemetry tracing setup for the Financial Agent.
Provides distributed tracing for retrieval, tool usage, and agent operations.
"""

import os
import logging
from typing import Optional
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)


class TelemetryManager:
    """Manages OpenTelemetry tracing configuration and spans."""
    
    def __init__(self):
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self._setup_tracing()
    
    def _setup_tracing(self):
        """Initialize OpenTelemetry with OTLP and optional Jaeger export."""
        service_name = os.getenv("OTEL_SERVICE_NAME", "financial-agent")
        
        # Create resource with service information
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
        })
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Add console exporter for development
        if os.getenv("LOG_LEVEL") == "DEBUG":
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )
        
        # Add OTLP exporter for Jaeger/Azure Monitor
        if os.getenv("JAEGER_ENABLED", "false").lower() == "true":
            otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
            try:
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
                self.tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
                logger.info(f"OTLP exporter configured for {otlp_endpoint}")
            except Exception as e:
                logger.warning(f"Failed to configure OTLP exporter: {e}")
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        # Get tracer
        self.tracer = trace.get_tracer(__name__)
        logger.info("OpenTelemetry tracing initialized")
    
    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Optional[dict] = None):
        """
        Context manager for tracing operations.
        
        Args:
            operation_name: Name of the operation being traced
            attributes: Optional attributes to add to the span
            
        Yields:
            The active span
        """
        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    if value is not None:
                        span.set_attribute(key, str(value))
            
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    def add_event(self, event_name: str, attributes: Optional[dict] = None):
        """Add an event to the current span."""
        span = trace.get_current_span()
        if span:
            span.add_event(event_name, attributes or {})
    
    def shutdown(self):
        """Shutdown the tracer provider and flush remaining spans."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("Tracing shutdown complete")


# Global telemetry instance
_telemetry: Optional[TelemetryManager] = None


def get_telemetry() -> TelemetryManager:
    """Get or create the global telemetry manager."""
    global _telemetry
    if _telemetry is None:
        _telemetry = TelemetryManager()
    return _telemetry


def trace_function(operation_name: Optional[str] = None):
    """
    Decorator for tracing functions.
    
    Args:
        operation_name: Optional custom operation name (defaults to function name)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            telemetry = get_telemetry()
            
            with telemetry.trace_operation(op_name) as span:
                # Add function arguments as attributes
                span.set_attribute("function.name", func.__name__)
                
                result = func(*args, **kwargs)
                return result
        
        return wrapper
    return decorator
