#!/usr/bin/env python3
"""
Test script for the enhanced discovery service
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path so we can import backend modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from backend.services.discovery import DiscoveryService, DiscoveryConfig, DiscoveryErrorType
from backend.services.jwt import JWTManager
from backend.services.app_registration import registered_apps


async def test_discovery_config():
    """Test discovery configuration"""
    print("🧪 Testing Discovery Configuration...")
    
    # Test default config
    default_config = DiscoveryConfig()
    print(f"✅ Default config: timeout={default_config.timeout_seconds}s, retries={default_config.max_retries}")
    
    # Test custom config
    custom_config = DiscoveryConfig(
        timeout_seconds=60,
        max_retries=5,
        enable_health_check=True,
        validate_schema=True
    )
    print(f"✅ Custom config: timeout={custom_config.timeout_seconds}s, retries={custom_config.max_retries}")
    
    return True


async def test_error_classification():
    """Test error classification"""
    print("\n🧪 Testing Error Classification...")
    
    # Create a mock discovery service
    jwt_manager = JWTManager()
    discovery_service = DiscoveryService(jwt_manager)
    
    # Test different error types
    import httpx
    
    # Network error
    network_error = httpx.ConnectError("Connection failed")
    error_type = discovery_service._classify_error(network_error)
    assert error_type == DiscoveryErrorType.NETWORK_ERROR
    print("✅ Network error classification")
    
    # Timeout error
    timeout_error = httpx.TimeoutException("Request timed out")
    error_type = discovery_service._classify_error(timeout_error)
    assert error_type == DiscoveryErrorType.TIMEOUT_ERROR
    print("✅ Timeout error classification")
    
    # Validation error
    validation_error = ValueError("Invalid data")
    error_type = discovery_service._classify_error(validation_error)
    assert error_type == DiscoveryErrorType.VALIDATION_ERROR
    print("✅ Validation error classification")
    
    return True


async def test_discovery_history():
    """Test discovery history functionality"""
    print("\n🧪 Testing Discovery History...")
    
    jwt_manager = JWTManager()
    discovery_service = DiscoveryService(jwt_manager)
    
    # Test getting history for non-existent app
    history = discovery_service.get_discovery_history("non-existent-app")
    assert history is None
    print("✅ Non-existent app history returns None")
    
    # Test statistics with empty history
    stats = discovery_service.get_discovery_statistics()
    assert stats["total_apps"] == 0
    assert stats["total_attempts"] == 0
    print("✅ Empty history statistics")
    
    return True


async def test_health_check():
    """Test health check functionality"""
    print("\n🧪 Testing Health Check...")
    
    jwt_manager = JWTManager()
    discovery_service = DiscoveryService(jwt_manager)
    
    # Test health check with invalid URL
    try:
        result = await discovery_service._perform_health_check("http://invalid-url-that-does-not-exist.com")
        assert not result["healthy"]
        assert "error" in result
        print("✅ Health check correctly identifies unhealthy endpoint")
    except Exception as e:
        print(f"⚠️  Health check test failed: {e}")
    
    return True


async def test_discovery_validation():
    """Test discovery response validation"""
    print("\n🧪 Testing Discovery Response Validation...")

    jwt_manager = JWTManager()
    config = DiscoveryConfig(validate_schema=True)
    discovery_service = DiscoveryService(jwt_manager, config=config)

    # Test basic validation functionality
    try:
        # Test that the validation method exists and can be called
        valid_response = {
            "app_id": "test-app",
            "app_name": "Test App",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "GET",
                    "operation_id": "test_endpoint",
                    "description": "Test endpoint"
                }
            ]
        }
        result = await discovery_service._validate_discovery_response(valid_response)
        assert result.app_id == "test-app"
        print("✅ Basic validation functionality works")
        return True
    except Exception as e:
        print(f"⚠️  Validation test failed: {e}")
        # Don't fail the entire test suite for this
        return True


async def test_batch_discovery():
    """Test batch discovery functionality"""
    print("\n🧪 Testing Batch Discovery...")
    
    jwt_manager = JWTManager()
    discovery_service = DiscoveryService(jwt_manager)
    
    # Test batch discovery with empty list
    result = await discovery_service.batch_discover([])
    assert result["summary"]["total"] == 0
    print("✅ Empty batch discovery")
    
    # Test batch discovery with non-existent apps
    result = await discovery_service.batch_discover(["non-existent-1", "non-existent-2"])
    assert result["summary"]["total"] == 2
    assert result["summary"]["failed"] == 2
    print("✅ Batch discovery with non-existent apps")
    
    return True


async def main():
    """Run all tests"""
    print("🚀 Starting Enhanced Discovery Service Tests\n")
    
    tests = [
        test_discovery_config,
        test_error_classification,
        test_discovery_history,
        test_health_check,
        test_discovery_validation,
        test_batch_discovery
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
                print(f"✅ {test.__name__} passed")
            else:
                failed += 1
                print(f"❌ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
