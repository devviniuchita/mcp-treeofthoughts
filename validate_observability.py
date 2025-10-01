#!/usr/bin/env python3
"""
Simple validation script for MCP TreeOfThoughts observability system.
Tests basic functionality without requiring a full Python environment.
"""


def validate_metrics_syntax():
    """Validate the metrics module syntax and basic functionality."""

    print("🔍 Validating MCP TreeOfThoughts Observability System...")

    try:
        # Test imports
        print("  ✓ Testing imports...")
        import os
        import sys

        # Add src to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

        # Test Prometheus client
        try:
            import prometheus_client

            print("  ✓ Prometheus client available")
        except ImportError:
            print(
                "  ❌ Prometheus client not available - install with: pip install prometheus-client"
            )
            return False

        # Test psutil
        try:
            import psutil

            print("  ✓ psutil available")
        except ImportError:
            print("  ❌ psutil not available - install with: pip install psutil")
            return False

        # Test metrics module syntax
        try:
            from monitoring.metrics import HealthChecker
            from monitoring.metrics import MetricsCollector

            print("  ✓ Metrics module imported successfully")
        except Exception as e:
            print(f"  ❌ Metrics module import failed: {e}")
            return False

        # Test metrics collector instantiation
        try:
            collector = MetricsCollector()
            print("  ✓ MetricsCollector instantiated")
        except Exception as e:
            print(f"  ❌ MetricsCollector instantiation failed: {e}")
            return False

        # Test health checker
        try:
            health_results = HealthChecker.run_all_checks()
            print(f"  ✓ Health checker executed: {health_results}")
        except Exception as e:
            print(f"  ❌ Health checker failed: {e}")
            return False

        # Test metrics generation
        try:
            collector.record_http_request("GET", "/test", 200, 0.1)
            collector.record_jwt_generation("RS256", "test")
            metrics_output = collector.get_metrics()
            assert "mcp_http_requests_total" in metrics_output
            print("  ✓ Metrics generation successful")
        except Exception as e:
            print(f"  ❌ Metrics generation failed: {e}")
            return False

        print("🎉 All observability system validations passed!")
        return True

    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        return False


def validate_integration():
    """Validate integration with Flask validation server."""

    print("\n🔗 Validating Flask Integration...")

    try:
        # Check if validation_server.py has the correct imports
        with open('validation_server.py', 'r') as f:
            content = f.read()

        # Check for metrics imports
        if "from src.monitoring.metrics import metrics_collector" in content:
            print("  ✓ Metrics imports found in validation_server.py")
        else:
            print("  ❌ Missing metrics imports in validation_server.py")
            return False

        # Check for track_http_request decorators
        if "@track_http_request" in content:
            print("  ✓ HTTP request tracking decorators found")
        else:
            print("  ❌ Missing HTTP request tracking decorators")
            return False

        # Check for metrics endpoint
        if "/metrics" in content:
            print("  ✓ Metrics endpoint found")
        else:
            print("  ❌ Missing metrics endpoint")
            return False

        print("🎉 Flask integration validation passed!")
        return True

    except Exception as e:
        print(f"❌ Flask integration validation failed: {e}")
        return False


def main():
    """Main validation function."""

    print("=" * 60)
    print("MCP TreeOfThoughts Observability System Validation")
    print("=" * 60)

    # Run validations
    syntax_ok = validate_metrics_syntax()
    integration_ok = validate_integration()

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    if syntax_ok and integration_ok:
        print("🎉 ALL VALIDATIONS PASSED - Observability system is ready!")
        print("\nNext steps:")
        print("1. Start validation server: python validation_server.py")
        print("2. Access metrics endpoint: curl http://localhost:5173/metrics")
        print("3. Check health endpoint: curl http://localhost:5173/health")
        return 0
    else:
        print("❌ SOME VALIDATIONS FAILED - Check errors above")
        print("\nRequired actions:")
        if not syntax_ok:
            print("- Fix metrics module syntax errors")
            print("- Install missing dependencies (prometheus-client, psutil)")
        if not integration_ok:
            print("- Fix Flask integration issues")
        return 1


if __name__ == "__main__":
    exit(main())
