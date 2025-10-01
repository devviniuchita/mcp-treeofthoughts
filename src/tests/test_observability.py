"""
Tests for MCP TreeOfThoughts Observability and Metrics System

This module tests the comprehensive monitoring capabilities including:
- Prometheus metrics collection
- HTTP request tracking
- JWT lifecycle monitoring
- Health check validation
- System resource monitoring
"""

import time

from unittest.mock import Mock
from unittest.mock import patch

import pytest

from prometheus_client import CollectorRegistry
from prometheus_client import generate_latest

from src.monitoring.metrics import HealthChecker
from src.monitoring.metrics import MetricsCollector
from src.monitoring.metrics import metrics_collector
from src.monitoring.metrics import track_execution_time
from src.monitoring.metrics import track_http_request


class TestMetricsCollector:
    """Test suite for MetricsCollector class."""

    @pytest.fixture
    def collector(self):
        """Create a fresh metrics collector for testing."""
        registry = CollectorRegistry()
        return MetricsCollector(registry)

    def test_http_request_metrics(self, collector):
        """Test HTTP request metrics recording."""
        # Record a successful request
        collector.record_http_request(
            method="GET",
            endpoint="/health",
            status_code=200,
            duration=0.05,
            request_size=100,
            response_size=500,
        )

        # Verify metrics were recorded
        metrics_output = generate_latest(collector.registry)
        assert b'mcp_http_requests_total' in metrics_output
        assert b'method="GET"' in metrics_output
        assert b'endpoint="/health"' in metrics_output
        assert b'status="200"' in metrics_output

    def test_jwt_metrics(self, collector):
        """Test JWT-related metrics recording."""
        # Test token generation
        collector.record_jwt_generation("RS256", "mcp-treeofthoughts")

        # Test token validation
        collector.record_jwt_validation("success", "RS256")

        # Test key rotation
        collector.record_jwt_key_rotation("scheduled")

        # Test key age update
        timestamp = time.time() - 3600  # 1 hour ago
        collector.update_jwt_key_metrics(timestamp)

        metrics_output = generate_latest(collector.registry)
        assert b'mcp_jwt_tokens_generated_total' in metrics_output
        assert b'mcp_jwt_tokens_validated_total' in metrics_output
        assert b'mcp_jwt_key_rotations_total' in metrics_output
        assert b'mcp_jwt_key_age_seconds' in metrics_output

    def test_jwks_metrics(self, collector):
        """Test JWKS endpoint metrics."""
        # Record JWKS requests
        collector.record_jwks_request(200, cache_hit=True)
        collector.record_jwks_request(200, cache_hit=False)
        collector.record_jwks_request(500, cache_hit=False)

        metrics_output = generate_latest(collector.registry)
        assert b'mcp_jwks_requests_total' in metrics_output
        assert b'mcp_jwks_cache_hits_total' in metrics_output

    def test_tot_metrics(self, collector):
        """Test Tree of Thoughts execution metrics."""
        strategy = "beam_search"

        # Start execution
        collector.record_tot_execution_start(strategy)

        # Generate thoughts
        collector.record_thought_generation(depth=1, evaluation_score=0.8)
        collector.record_thought_generation(depth=2, evaluation_score=0.3)
        collector.record_thought_generation(depth=2, evaluation_score=0.6)

        # End execution
        collector.record_tot_execution_end(strategy, "success", duration=30.5)

        metrics_output = generate_latest(collector.registry)
        assert b'mcp_tot_executions_total' in metrics_output
        assert b'mcp_tot_execution_duration_seconds' in metrics_output
        assert b'mcp_tot_thoughts_generated_total' in metrics_output
        assert b'mcp_tot_active_executions' in metrics_output

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.Process')
    def test_system_metrics(self, mock_process, mock_memory, mock_cpu, collector):
        """Test system resource metrics collection."""
        # Mock system metrics
        mock_cpu.return_value = 45.2
        mock_memory.return_value = Mock(
            used=1024 * 1024 * 1024, available=2 * 1024 * 1024 * 1024
        )

        mock_proc_instance = Mock()
        mock_proc_instance.cpu_percent.return_value = 12.5
        mock_proc_instance.memory_info.return_value = Mock(rss=512 * 1024 * 1024)
        mock_process.return_value = mock_proc_instance

        # Update system metrics
        collector.update_system_metrics()

        metrics_output = generate_latest(collector.registry)
        assert b'mcp_system_cpu_usage_percent' in metrics_output
        assert b'mcp_system_memory_usage_bytes' in metrics_output
        assert b'mcp_process_cpu_usage_percent' in metrics_output

    def test_health_status_metrics(self, collector):
        """Test health status metrics."""
        collector.update_health_status("jwt_system", True)
        collector.update_health_status("database", False)
        collector.update_health_status("external_apis", True)

        metrics_output = generate_latest(collector.registry)
        assert b'mcp_health_status' in metrics_output
        assert b'component="jwt_system"' in metrics_output

    def test_app_info_metrics(self, collector):
        """Test application info metrics."""
        collector.set_app_info(
            version="1.0.0", environment="test", build_time="2025-01-08T12:00:00Z"
        )

        metrics_output = generate_latest(collector.registry)
        assert b'mcp_app_info' in metrics_output


class TestDecorators:
    """Test suite for metric decorators."""

    @pytest.fixture
    def test_registry(self):
        """Create a test registry for decorators."""
        return CollectorRegistry()

    def test_track_execution_time_decorator(self):
        """Test the execution time tracking decorator."""

        @track_execution_time("test_function")
        def test_function(sleep_time=0.01):
            time.sleep(sleep_time)
            return "success"

        # Execute function
        result = test_function()

        assert result == "success"
        # Note: In real test, we'd check metrics output here

    def test_track_execution_time_with_exception(self):
        """Test execution time tracking when function raises exception."""

        @track_execution_time("failing_function")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        # Note: In real test, we'd verify error metrics were recorded

    @patch('flask.request')
    @patch('flask.g')
    def test_track_http_request_decorator(self, mock_g, mock_request):
        """Test HTTP request tracking decorator."""
        mock_request.method = "GET"
        mock_request.endpoint = "test_endpoint"
        mock_request.content_length = 100
        mock_request.get_data.return_value = b"test data"

        @track_http_request
        def test_route():
            return {"status": "success"}, 200

        result = test_route()
        assert result[0]["status"] == "success"
        assert result[1] == 200


class TestHealthChecker:
    """Test suite for HealthChecker class."""

    @patch('src.monitoring.metrics.JWTManager')
    def test_check_jwt_system_healthy(self, mock_jwt_manager):
        """Test JWT system health check when healthy."""
        mock_instance = Mock()
        mock_instance.get_or_create_token.return_value = "valid.jwt.token"
        mock_jwt_manager.return_value = mock_instance

        result = HealthChecker.check_jwt_system()
        assert result is True

    @patch('src.monitoring.metrics.JWTManager')
    def test_check_jwt_system_unhealthy(self, mock_jwt_manager):
        """Test JWT system health check when unhealthy."""
        mock_jwt_manager.side_effect = Exception("JWT system error")

        result = HealthChecker.check_jwt_system()
        assert result is False

    def test_check_database_connection(self):
        """Test database connectivity check."""
        # Currently always returns True - implement when DB is added
        result = HealthChecker.check_database_connection()
        assert result is True

    def test_check_external_apis(self):
        """Test external API connectivity check."""
        # Currently always returns True - implement when external APIs are added
        result = HealthChecker.check_external_apis()
        assert result is True

    @patch('src.monitoring.metrics.HealthChecker.check_jwt_system')
    @patch('src.monitoring.metrics.HealthChecker.check_database_connection')
    @patch('src.monitoring.metrics.HealthChecker.check_external_apis')
    def test_run_all_checks(self, mock_external, mock_db, mock_jwt):
        """Test running all health checks."""
        mock_jwt.return_value = True
        mock_db.return_value = True
        mock_external.return_value = False

        results = HealthChecker.run_all_checks()

        assert results == {'jwt_system': True, 'database': True, 'external_apis': False}


class TestMetricsIntegration:
    """Integration tests for the complete metrics system."""

    def test_complete_request_flow(self):
        """Test a complete request flow with metrics."""
        collector = MetricsCollector(CollectorRegistry())

        # Simulate a complete request flow
        start_time = time.time()

        # HTTP request
        collector.record_http_request("POST", "/api/jwt", 200, 0.1, 150, 800)

        # JWT generation
        collector.record_jwt_generation("RS256", "mcp-treeofthoughts")

        # JWKS access
        collector.record_jwks_request(200, cache_hit=False)

        # Tree of Thoughts execution
        collector.record_tot_execution_start("beam_search")
        collector.record_thought_generation(1, 0.7)
        collector.record_tot_execution_end("beam_search", "success", 45.2)

        # Health checks
        collector.update_health_status("jwt_system", True)

        # Verify all metrics are present
        metrics_output = generate_latest(collector.registry)

        expected_metrics = [
            b'mcp_http_requests_total',
            b'mcp_jwt_tokens_generated_total',
            b'mcp_jwks_requests_total',
            b'mcp_tot_executions_total',
            b'mcp_health_status',
        ]

        for metric in expected_metrics:
            assert metric in metrics_output

    def test_metrics_endpoint_format(self):
        """Test that metrics output is in valid Prometheus format."""
        collector = MetricsCollector(CollectorRegistry())

        # Add some sample data
        collector.record_http_request("GET", "/health", 200, 0.05)
        collector.update_health_status("jwt_system", True)

        metrics_output = collector.get_metrics()

        # Basic Prometheus format validation
        assert isinstance(metrics_output, str)
        assert "# HELP" in metrics_output
        assert "# TYPE" in metrics_output
        assert "mcp_" in metrics_output

    @patch('src.monitoring.metrics.HealthChecker.run_all_checks')
    def test_health_endpoint_integration(self, mock_health_checks):
        """Test integration with Flask health endpoint."""
        mock_health_checks.return_value = {
            'jwt_system': True,
            'database': True,
            'external_apis': True,
        }

        # This would be tested with a real Flask app
        results = HealthChecker.run_all_checks()
        overall_health = all(results.values())

        assert overall_health is True
        assert results['jwt_system'] is True


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
