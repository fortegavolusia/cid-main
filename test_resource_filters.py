"""
Tests for CID Resource Filter v1 System
"""
import pytest
import json
import hmac
import hashlib
from unittest.mock import MagicMock
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Import from our modules
import sys
sys.path.append('azure-auth-app')
sys.path.append('test-app')

from resource_filter_policy import PolicyCompiler, RolePolicy, PolicyStore
from app_resource_filter import enforce, policy_cache, verify_cid_signature

Base = declarative_base()

class TestWorkOrder(Base):
    __tablename__ = "test_work_orders"
    id = Column(Integer, primary_key=True)
    department = Column(String)
    owner_id = Column(String)
    created_by = Column(String)

def test_policy_compilation():
    """Unit test: Compile role filters to policy JSON"""
    compiler = PolicyCompiler()
    
    resource_perms = {
        "work_order": {
            "actions": ["read", "update"],
            "filters": [
                {"type": "department", "field": "department"},
                {"type": "ownership", "field": "owner_id"}
            ]
        }
    }
    
    policy = compiler.compile_filters("DPW_EDITOR", 1, resource_perms)
    
    assert policy.role == "DPW_EDITOR"
    assert policy.version == 1
    assert len(policy.scopes) == 1
    
    scope = policy.scopes[0]
    assert scope.resource_type == "work_order"
    assert "read" in scope.actions
    assert "update" in scope.actions
    assert len(scope.clauses) == 2
    
    # Check department clause
    dept_clause = scope.clauses[0]
    assert dept_clause.department == "{user.department}"
    
    # Check ownership clause
    owner_clause = scope.clauses[1]
    assert owner_clause.ownership["field"] == "owner_id"
    assert owner_clause.ownership["equals"] == "{user.id}"

def test_sqlalchemy_filter_generation():
    """Unit test: Clause compilation to SQLAlchemy WHERE conditions"""
    # Setup test database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Add test data
    session.add(TestWorkOrder(id=1, department="IT", owner_id="user_1", created_by="user_1"))
    session.add(TestWorkOrder(id=2, department="HR", owner_id="user_2", created_by="user_2"))
    session.add(TestWorkOrder(id=3, department="IT", owner_id="user_3", created_by="user_3"))
    session.commit()
    
    # Create policy
    policy = RolePolicy(
        role="TEST_ROLE",
        version=1,
        scopes=[{
            "resource_type": "work_order",
            "actions": ["read"],
            "clauses": [
                {"department": "{user.department}"},
                {"ownership": {"field": "owner_id", "equals": "{user.id}"}}
            ]
        }]
    )
    
    # User context
    user_ctx = {"id": "user_1", "department": "IT"}
    
    # Column mapping
    colmap = {
        "department": TestWorkOrder.department,
        "owner_id": TestWorkOrder.owner_id
    }
    
    # Apply filter
    query = session.query(TestWorkOrder)
    filtered_query = enforce(
        query, "work_order", "read", user_ctx, [policy], colmap
    )
    
    results = filtered_query.all()
    
    # Should return IT items (1,3) and owned items (1)
    # Combined with OR, should get items 1 and 3
    assert len(results) == 2
    assert results[0].id in [1, 3]
    assert results[1].id in [1, 3]

def test_e2e_publish_receive_policy():
    """E2E test: Publish role v1 → app receives policy"""
    # Simulate policy publish
    store = PolicyStore(data_dir="/tmp/test_policies")
    
    policy = RolePolicy(
        role="DPW_EDITOR",
        version=1,
        scopes=[{
            "resource_type": "work_order",
            "actions": ["read", "update"],
            "clauses": [{"department": "{user.department}"}]
        }]
    )
    
    # Save policy
    version = store.save_policy("workorders", "DPW_EDITOR", policy)
    assert version == 1
    
    # Simulate webhook receipt
    policy_cache.set("DPW_EDITOR", 1, policy)
    
    # Verify cache
    cached = policy_cache.get("DPW_EDITOR", 1)
    assert cached is not None
    assert cached.role == "DPW_EDITOR"
    assert cached.version == 1

def test_e2e_policy_update():
    """E2E test: Publish v2 → new policy cached, old JWT still works"""
    # Initial policy v1
    policy_v1 = RolePolicy(
        role="DPW_EDITOR",
        version=1,
        scopes=[{
            "resource_type": "work_order",
            "actions": ["read"],
            "clauses": [{"department": "{user.department}"}]
        }]
    )
    
    policy_cache.set("DPW_EDITOR", 1, policy_v1)
    
    # Update to v2 with more permissions
    policy_v2 = RolePolicy(
        role="DPW_EDITOR",
        version=2,
        scopes=[{
            "resource_type": "work_order",
            "actions": ["read", "update", "delete"],
            "clauses": [
                {"department": "{user.department}"},
                {"ownership": {"field": "owner_id", "equals": "{user.id}"}}
            ]
        }]
    )
    
    policy_cache.set("DPW_EDITOR", 2, policy_v2)
    
    # Old JWT with v1 should still work
    old_policy = policy_cache.get("DPW_EDITOR", 1)
    assert old_policy is not None
    assert len(old_policy.scopes[0].actions) == 1
    
    # New JWT with v2 gets updated policy
    new_policy = policy_cache.get("DPW_EDITOR", 2)
    assert new_policy is not None
    assert len(new_policy.scopes[0].actions) == 3
    assert len(new_policy.scopes[0].clauses) == 2

def test_hmac_signature_verification():
    """Test HMAC signature generation and verification"""
    secret = "test-secret"
    payload = json.dumps({"app": "workorders", "policies": []}).encode()
    
    # Generate signature
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    signature = f"sha256={expected}"
    
    # Mock the secret in app
    import app_resource_filter
    original_secret = app_resource_filter.CID_WEBHOOK_SECRET
    app_resource_filter.CID_WEBHOOK_SECRET = secret
    
    # Verify
    assert verify_cid_signature(payload, signature) == True
    
    # Test with wrong signature
    assert verify_cid_signature(payload, "sha256=wrong") == False
    
    # Restore
    app_resource_filter.CID_WEBHOOK_SECRET = original_secret

if __name__ == "__main__":
    # Run tests
    test_policy_compilation()
    print("✓ Policy compilation test passed")
    
    test_sqlalchemy_filter_generation()
    print("✓ SQLAlchemy filter generation test passed")
    
    test_e2e_publish_receive_policy()
    print("✓ E2E publish/receive test passed")
    
    test_e2e_policy_update()
    print("✓ E2E policy update test passed")
    
    test_hmac_signature_verification()
    print("✓ HMAC signature test passed")
    
    print("\n✅ All tests passed!")