"""
MCP TreeOfThoughts - Observability and Metrics Module

This module provides comprehensive monitoring capabilities for the MCP TreeOfThoughts
system, including JWT operations, HTTP requests, and business metrics.

Features:
- Prometheus metrics collection
- JWT lifecycle tracking
- HTTP request/response monitoring
- Business logic metrics (Tree of Thoughts operations)
- Health and performance indicators
"""

import logging
import time

from functools import wraps
from typing import Any
from typing import Dict
from typing import Optional

import psutil

from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import REGISTRY
from prometheus_client import CollectorRegistry
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from prometheus_client import Info
from prometheus_client import generate_latest


logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Centralized metrics collector for MCP TreeOfThoughts system.

    Provides standardized metrics collection following Prometheus best practices
    and the Four Golden Signals approach (Latency, Traffic, Errors, Saturation).
    """

    def __init__(self, registry: CollectorRegistry = REGISTRY):
        self.registry = registry
        self._initialize_metrics()

    def _initialize_metrics(self):
        """Initialize all Prometheus metrics."""

        # === HTTP Request Metrics (Traffic & Latency) ===
        self.http_requests_total = Counter(
            'mcp_http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry,
        )

        self.http_request_duration_seconds = Histogram(
            'mcp_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry,
        )

        self.http_request_size_bytes = Histogram(
            'mcp_http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            registry=self.registry,
        )

        self.http_response_size_bytes = Histogram(
            'mcp_http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint', 'status'],
            registry=self.registry,
        )

        # === JWT Authentication Metrics ===
        self.jwt_tokens_generated_total = Counter(
            'mcp_jwt_tokens_generated_total',
            'Total number of JWT tokens generated',
            ['algorithm', 'issuer'],
            registry=self.registry,
        )

        self.jwt_tokens_validated_total = Counter(
            'mcp_jwt_tokens_validated_total',
            'Total number of JWT token validations',
            ['status', 'algorithm'],
            registry=self.registry,
        )

        self.jwt_key_rotations_total = Counter(
            'mcp_jwt_key_rotations_total',
            'Total number of JWT key rotations',
            ['reason'],
            registry=self.registry,
        )

        self.jwt_key_age_seconds = Gauge(
            'mcp_jwt_key_age_seconds',
            'Age of current JWT signing key in seconds',
            registry=self.registry,
        )

        self.jwt_key_created_timestamp = Gauge(
            'mcp_jwt_key_created_timestamp',
            'Timestamp when current JWT key was created',
            registry=self.registry,
        )

        # === JWKS Endpoint Metrics ===
        self.jwks_requests_total = Counter(
            'mcp_jwks_requests_total',
            'Total number of JWKS endpoint requests',
            ['status'],
            registry=self.registry,
        )

        self.jwks_cache_hits_total = Counter(
            'mcp_jwks_cache_hits_total',
            'Total number of JWKS cache hits',
            registry=self.registry,
        )

        # === Business Logic Metrics (Tree of Thoughts) ===
        self.tot_executions_total = Counter(
            'mcp_tot_executions_total',
            'Total number of Tree of Thoughts executions',
            ['strategy', 'status'],
            registry=self.registry,
        )

        self.tot_execution_duration_seconds = Histogram(
            'mcp_tot_execution_duration_seconds',
            'Tree of Thoughts execution duration in seconds',
            ['strategy'],
            buckets=(1, 5, 10, 30, 60, 300, 600, 1800),
            registry=self.registry,
        )

        self.tot_thoughts_generated_total = Counter(
            'mcp_tot_thoughts_generated_total',
            'Total number of thoughts generated',
            ['depth', 'evaluation_score_range'],
            registry=self.registry,
        )

        self.tot_active_executions = Gauge(
            'mcp_tot_active_executions',
            'Number of currently active Tree of Thoughts executions',
            registry=self.registry,
        )

        # === System Health Metrics (Saturation) ===
        self.system_cpu_usage_percent = Gauge(
            'mcp_system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry,
        )

        self.system_memory_usage_bytes = Gauge(
            'mcp_system_memory_usage_bytes',
            'System memory usage in bytes',
            registry=self.registry,
        )

        self.system_memory_available_bytes = Gauge(
            'mcp_system_memory_available_bytes',
            'System memory available in bytes',
            registry=self.registry,
        )

        self.process_cpu_usage_percent = Gauge(
            'mcp_process_cpu_usage_percent',
            'Process CPU usage percentage',
            registry=self.registry,
        )

        self.process_memory_usage_bytes = Gauge(
            'mcp_process_memory_usage_bytes',
            'Process memory usage in bytes',
            registry=self.registry,
        )

        # === Application Info ===
        self.app_info = Info(
            'mcp_app_info', 'Application information', registry=self.registry
        )

        # === Health Status ===
        self.health_status = Gauge(
            'mcp_health_status',
            'Application health status (1=healthy, 0=unhealthy)',
            ['component'],
            registry=self.registry,
        )

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
    ):
        """Record HTTP request metrics."""
        status = str(status_code)

        self.http_requests_total.labels(
            method=method, endpoint=endpoint, status=status
        ).inc()

        self.http_request_duration_seconds.labels(
            method=method, endpoint=endpoint
        ).observe(duration)

        if request_size is not None:
            self.http_request_size_bytes.labels(
                method=method, endpoint=endpoint
            ).observe(request_size)

        if response_size is not None:
            self.http_response_size_bytes.labels(
                method=method, endpoint=endpoint, status=status
            ).observe(response_size)

    def record_jwt_generation(self, algorithm: str, issuer: str):
        """Record JWT token generation."""
        self.jwt_tokens_generated_total.labels(algorithm=algorithm, issuer=issuer).inc()

    def record_jwt_validation(self, status: str, algorithm: str):
        """Record JWT token validation."""
        self.jwt_tokens_validated_total.labels(status=status, algorithm=algorithm).inc()

    def record_jwt_key_rotation(self, reason: str):
        """Record JWT key rotation event."""
        self.jwt_key_rotations_total.labels(reason=reason).inc()

    def update_jwt_key_metrics(self, key_created_timestamp: float):
        """Update JWT key age metrics."""
        current_time = time.time()
        key_age = current_time - key_created_timestamp

        self.jwt_key_created_timestamp.set(key_created_timestamp)
        self.jwt_key_age_seconds.set(key_age)

    def record_jwks_request(self, status_code: int, cache_hit: bool = False):
        """Record JWKS endpoint request."""
        self.jwks_requests_total.labels(status=str(status_code)).inc()
        if cache_hit:
            self.jwks_cache_hits_total.inc()

    def record_tot_execution_start(self, strategy: str):
        """Record start of Tree of Thoughts execution."""
        self.tot_active_executions.inc()

    def record_tot_execution_end(self, strategy: str, status: str, duration: float):
        """Record end of Tree of Thoughts execution."""
        self.tot_active_executions.dec()
        self.tot_executions_total.labels(strategy=strategy, status=status).inc()
        self.tot_execution_duration_seconds.labels(strategy=strategy).observe(duration)

    def record_thought_generation(self, depth: int, evaluation_score: float):
        """Record generation of a thought."""
        # Categorize evaluation score
        if evaluation_score < 0.3:
            score_range = "low"
        elif evaluation_score < 0.7:
            score_range = "medium"
        else:
            score_range = "high"

        self.tot_thoughts_generated_total.labels(
            depth=str(depth), evaluation_score_range=score_range
        ).inc()

    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.system_cpu_usage_percent.set(cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            self.system_memory_usage_bytes.set(memory.used)
            self.system_memory_available_bytes.set(memory.available)

            # Process metrics
            process = psutil.Process()
            process_cpu = process.cpu_percent()
            process_memory = process.memory_info().rss

            self.process_cpu_usage_percent.set(process_cpu)
            self.process_memory_usage_bytes.set(process_memory)

        except Exception as e:
            logger.warning(f"Failed to update system metrics: {e}")

    def set_app_info(self, version: str, environment: str, build_time: str):
        """Set application information."""
        self.app_info.info(
            {
                'version': version,
                'environment': environment,
                'build_time': build_time,
                'python_version': f"{psutil.version_info}",
            }
        )

    def update_health_status(self, component: str, is_healthy: bool):
        """Update component health status."""
        self.health_status.labels(component=component).set(1 if is_healthy else 0)

    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format."""
        # Update system metrics before returning
        self.update_system_metrics()
        return generate_latest(self.registry)


# Global metrics collector instance
metrics_collector = MetricsCollector()


def track_execution_time(metric_name: str = None):
    """
    Decorator to track execution time of functions.

    Args:
        metric_name: Optional custom metric name prefix
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time

                # Record execution time metric
                func_name = metric_name or f"{func.__module__}.{func.__name__}"

                # Create a custom histogram if needed
                if not hasattr(metrics_collector, f"_func_{func_name}_duration"):
                    hist = Histogram(
                        f'mcp_function_duration_seconds',
                        f'Duration of {func_name} function calls',
                        ['function', 'status'],
                        registry=metrics_collector.registry,
                    )
                    setattr(metrics_collector, f"_func_{func_name}_duration", hist)

                hist = getattr(metrics_collector, f"_func_{func_name}_duration")
                hist.labels(function=func_name, status=status).observe(duration)

        return wrapper

    return decorator


def track_http_request(func):
    """
    Decorator to automatically track HTTP request metrics for Flask routes.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import g
        from flask import request

        start_time = time.time()
        g.start_time = start_time

        try:
            response = func(*args, **kwargs)

            # Determine status code
            if hasattr(response, 'status_code'):
                status_code = response.status_code
            elif isinstance(response, tuple) and len(response) > 1:
                status_code = response[1]
            else:
                status_code = 200

            return response

        except Exception as e:
            status_code = 500
            raise

        finally:
            duration = time.time() - start_time

            # Extract endpoint name
            endpoint = request.endpoint or func.__name__
            method = request.method

            # Get request/response sizes
            request_size = request.content_length or len(request.get_data())

            # Record metrics
            metrics_collector.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration,
                request_size=request_size,
            )

    return wrapper


# Health check utilities
class HealthChecker:
    """Utility class for performing health checks on system components."""

    @staticmethod
    def check_jwt_system() -> bool:
        """Check if JWT system is healthy."""
        try:
            from ..jwt_manager import JWTManager

            jwt_manager = JWTManager()

            # Try to generate a token
            token = jwt_manager.get_or_create_token()
            return token is not None
        except Exception:
            return False

    @staticmethod
    def check_database_connection() -> bool:
        """Check database connectivity (if applicable)."""
        # Implement database health check
        return True

    @staticmethod
    def check_external_apis() -> bool:
        """Check external API connectivity."""
        # Implement external API health checks
        return True

    @classmethod
    def run_all_checks(cls) -> Dict[str, bool]:
        """Run all health checks and return results."""
        checks = {
            'jwt_system': cls.check_jwt_system(),
            'database': cls.check_database_connection(),
            'external_apis': cls.check_external_apis(),
        }

        # Update health metrics
        for component, is_healthy in checks.items():
            metrics_collector.update_health_status(component, is_healthy)

        return checks
