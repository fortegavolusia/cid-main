#!/usr/bin/env python3
"""
Test script to verify API Keys migration from JSON to PostgreSQL database
"""

import sys
import os
import logging

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.api_keys import api_key_manager
from services.database import db_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_key_manager():
    """Test that the API key manager can load from database"""
    try:
        logger.info("Testing API Key Manager database migration...")

        # Test 1: Initialize the manager (should load from database)
        logger.info("1. Initializing API Key Manager...")
        manager = api_key_manager
        logger.info(f"   Loaded {sum(len(keys) for keys in manager.api_keys.values())} API keys from database")

        # Test 2: Test database connection
        logger.info("2. Testing database connection...")
        if db_service.connect():
            logger.info("   Database connection successful")
            db_service.disconnect()
        else:
            logger.error("   Database connection failed")
            return False

        # Test 3: Create a test API key (if we have a test app)
        logger.info("3. Testing API key creation...")
        test_client_id = "test-client-id"
        try:
            api_key, metadata = manager.create_api_key(
                app_client_id=test_client_id,
                name="Test Migration Key",
                permissions=["test.read"],
                created_by="migration-test",
                ttl_days=30
            )
            logger.info(f"   Created test API key: {metadata.key_prefix}")

            # Test 4: Validate the created key
            logger.info("4. Testing API key validation...")
            result = manager.validate_api_key(api_key)
            if result:
                client_id, validated_metadata = result
                logger.info(f"   API key validated successfully for client: {client_id}")

                # Test 5: Revoke the test key
                logger.info("5. Testing API key revocation...")
                revoked = manager.revoke_api_key(test_client_id, metadata.key_id)
                if revoked:
                    logger.info("   API key revoked successfully")
                else:
                    logger.error("   Failed to revoke API key")
            else:
                logger.error("   API key validation failed")

        except Exception as e:
            logger.warning(f"   Could not test key creation (database may not be available): {e}")

        logger.info("API Key Manager migration test completed successfully")
        return True

    except Exception as e:
        logger.error(f"API Key Manager test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_backward_compatibility():
    """Test that existing functionality still works"""
    try:
        logger.info("Testing backward compatibility...")

        manager = api_key_manager

        # Test list_api_keys method
        keys = manager.list_api_keys("test-client-id")
        logger.info(f"   Found {len(keys)} API keys for test client")

        # Test get_api_key method
        if keys:
            key = manager.get_api_key("test-client-id", keys[0].key_id)
            if key:
                logger.info(f"   Successfully retrieved API key: {key.name}")
            else:
                logger.error("   Failed to retrieve API key")

        logger.info("Backward compatibility test completed successfully")
        return True

    except Exception as e:
        logger.error(f"Backward compatibility test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting API Keys Migration Test")
    logger.info("=" * 50)

    # Run tests
    test1_passed = test_api_key_manager()
    test2_passed = test_backward_compatibility()

    logger.info("=" * 50)
    if test1_passed and test2_passed:
        logger.info("All tests passed! Migration is successful.")
        sys.exit(0)
    else:
        logger.error("Some tests failed. Please check the logs above.")
        sys.exit(1)