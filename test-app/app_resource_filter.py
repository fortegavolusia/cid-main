"""
FastAPI Test App with CID Resource Filter Support
Demonstrates policy caching and enforcement
"""
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel
from datetime import datetime
import hmac
import hashlib
import json
import jwt
from collections import OrderedDict
from sqlalchemy import create_engine, Column, String, Integer, DateTime, or_, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

app = FastAPI(title="Work Orders App with Resource Filters")

# Configuration
CID_WEBHOOK_SECRET = "shared-secret-for-workorders-app"  # Should be in env
DATABASE_URL = "sqlite:///./workorders.db"

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class WorkOrder(Base):
    __tablename__ = "work_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    department = Column(String, index=True)
    owner_id = Column(String, index=True)
    created_by = Column(String, index=True)
    assigned_to = Column(String, index=True)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Policy models
class FilterClause(BaseModel):
    department: Optional[str] = None
    hierarchy: Optional[Dict[str, str]] = None
    ownership: Optional[Dict[str, str]] = None
    custom: Optional[Dict[str, str]] = None

class ResourceScope(BaseModel):
    resource_type: str
    actions: List[str]
    clauses: List[FilterClause]

class RolePolicy(BaseModel):
    role: str
    version: int
    scopes: List[ResourceScope]

class PolicyCache:
    """In-memory LRU cache for role policies"""
    
    def __init__(self, max_size: int = 50):
        self.cache: OrderedDict[tuple, RolePolicy] = OrderedDict()
        self.max_size = max_size
    
    def set(self, role: str, version: int, policy: RolePolicy):
        """Store policy in cache"""
        key = (role, version)
        
        # Remove if exists to update position
        if key in self.cache:
            del self.cache[key]
        
        # Add to end (most recent)
        self.cache[key] = policy
        
        # Evict oldest if over limit
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def get(self, role: str, version: int) -> Optional[RolePolicy]:
        """Get policy from cache"""
        key = (role, version)
        
        if key not in self.cache:
            return None
        
        # Move to end (most recent)
        self.cache.move_to_end(key)
        return self.cache[key]

# Initialize policy cache
policy_cache = PolicyCache()

def verify_cid_signature(payload: bytes, signature: str) -> bool:
    """Verify HMAC signature from CID"""
    expected = hmac.new(
        CID_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    expected_signature = f"sha256={expected}"
    return hmac.compare_digest(expected_signature, signature)

@app.post("/cid/policies")
async def receive_policies(request: Request, x_cid_signature: str = Header(...)):
    """Webhook endpoint to receive policy updates from CID"""
    # Get raw body
    body = await request.body()
    
    # Verify signature
    if not verify_cid_signature(body, x_cid_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    data = json.loads(body)
    app_name = data.get("app")
    policies = data.get("policies", [])
    
    # Update cache with new policies
    for policy_data in policies:
        policy = RolePolicy(**policy_data)
        policy_cache.set(policy.role, policy.version, policy)
    
    return JSONResponse({
        "status": "success",
        "policies_updated": len(policies)
    })

def get_policies_from_jwt(token: str, app_name: str) -> List[Dict[str, Any]]:
    """Extract role and version info from JWT for this app"""
    try:
        # Decode without verification for demo (in prod, verify!)
        claims = jwt.decode(token, options={"verify_signature": False})
        
        # Get CID section
        cid_claims = claims.get("cid", {})
        apps = cid_claims.get("apps", [])
        
        # Find our app
        for app_info in apps:
            if app_info["app"] == app_name:
                return app_info.get("roles", [])
        
        return []
    except Exception:
        return []

def resolve_hierarchy_ids(scope: str, user_id: str) -> Set[str]:
    """Resolve hierarchy scope to set of user IDs (stub implementation)"""
    # In real implementation, query org hierarchy service
    if scope == "subordinates":
        # Return mock subordinate IDs
        return {f"user_{i}" for i in range(10, 15)}
    elif scope == "all_subordinates":
        return {f"user_{i}" for i in range(10, 25)}
    elif scope == "peers":
        return {f"user_{i}" for i in range(5, 10)}
    elif scope == "team":
        return {f"user_{i}" for i in range(1, 10)}
    return {user_id}

def enforce(
    query,
    resource_type: str,
    action: str,
    user_ctx: Dict,
    role_policies: List[RolePolicy],
    colmap: Dict[str, Any]
):
    """Apply resource filters to SQLAlchemy query"""
    
    # Find applicable scopes
    applicable_clauses = []
    
    for policy in role_policies:
        for scope in policy.scopes:
            if scope.resource_type == resource_type and action in scope.actions:
                applicable_clauses.extend(scope.clauses)
    
    if not applicable_clauses:
        # No matching scope - deny access
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build filter conditions
    or_conditions = []
    
    for clause in applicable_clauses:
        and_conditions = []
        
        # Department filter
        if clause.department:
            dept_value = user_ctx.get("department")
            if dept_value and "department" in colmap:
                and_conditions.append(colmap["department"] == dept_value)
        
        # Ownership filter
        if clause.ownership:
            field = clause.ownership.get("field", "owner_id")
            if field in colmap:
                and_conditions.append(colmap[field] == user_ctx["id"])
        
        # Hierarchy filter
        if clause.hierarchy:
            field = clause.hierarchy.get("field", "created_by")
            scope = clause.hierarchy.get("scope", "subordinates")
            
            if field in colmap:
                ids = resolve_hierarchy_ids(scope, user_ctx["id"])
                and_conditions.append(colmap[field].in_(ids))
        
        # Custom filter
        if clause.custom:
            field = clause.custom.get("field")
            attr_path = clause.custom.get("equals", "").strip("{}")
            
            if field and field in colmap:
                # Extract attribute from user context
                attr_parts = attr_path.split(".")
                if attr_parts[0] == "user" and len(attr_parts) > 1:
                    attr_name = attr_parts[1]
                    attr_value = user_ctx.get(attr_name)
                    if attr_value:
                        and_conditions.append(colmap[field] == attr_value)
        
        # Combine conditions within clause (AND)
        if and_conditions:
            if len(and_conditions) == 1:
                or_conditions.append(and_conditions[0])
            else:
                or_conditions.append(and_(*and_conditions))
    
    # Apply combined filter (OR between clauses)
    if or_conditions:
        if len(or_conditions) == 1:
            query = query.filter(or_conditions[0])
        else:
            query = query.filter(or_(*or_conditions))
    
    return query

def get_db():
    """Dependency to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(authorization: str = Header(None)) -> Dict:
    """Extract user context from JWT"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    token = authorization[7:]
    
    try:
        # Decode without verification for demo
        claims = jwt.decode(token, options={"verify_signature": False})
        cid_claims = claims.get("cid", {})
        
        return {
            "id": cid_claims.get("uid"),
            "department": cid_claims.get("department"),
            "email": claims.get("email"),
            "groups": cid_claims.get("groups", [])
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/work-orders")
async def list_work_orders(
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user),
    authorization: str = Header(None)
):
    """List work orders with resource filtering applied"""
    # Get user's roles from JWT
    token = authorization[7:] if authorization else ""
    role_infos = get_policies_from_jwt(token, "workorders")
    
    # Get policies from cache
    policies = []
    for role_info in role_infos:
        role_name = role_info.get("name")
        version = role_info.get("ver", 1)
        
        policy = policy_cache.get(role_name, version)
        if policy:
            policies.append(policy)
    
    if not policies:
        return JSONResponse({"error": "No valid policies found"}, status_code=403)
    
    # Build base query
    query = db.query(WorkOrder)
    
    # Define column mapping
    colmap = {
        "department": WorkOrder.department,
        "owner_id": WorkOrder.owner_id,
        "created_by": WorkOrder.created_by,
        "assigned_to": WorkOrder.assigned_to
    }
    
    # Apply resource filters
    try:
        query = enforce(
            query=query,
            resource_type="work_order",
            action="read",
            user_ctx=user,
            role_policies=policies,
            colmap=colmap
        )
    except HTTPException as e:
        raise e
    
    # Execute query
    work_orders = query.all()
    
    return JSONResponse({
        "total": len(work_orders),
        "items": [
            {
                "id": wo.id,
                "title": wo.title,
                "department": wo.department,
                "owner_id": wo.owner_id,
                "status": wo.status,
                "created_at": wo.created_at.isoformat() if wo.created_at else None
            }
            for wo in work_orders
        ],
        "filters_applied": True,
        "user_department": user.get("department")
    })

@app.post("/work-orders/seed")
async def seed_data(db: Session = Depends(get_db)):
    """Seed test data"""
    # Clear existing
    db.query(WorkOrder).delete()
    
    # Add test data
    test_orders = [
        WorkOrder(title="Fix printer", department="IT", owner_id="user_1", created_by="user_1", status="open"),
        WorkOrder(title="Replace light", department="Facilities", owner_id="user_2", created_by="user_2", status="open"),
        WorkOrder(title="Network issue", department="IT", owner_id="user_3", created_by="user_1", status="closed"),
        WorkOrder(title="Clean office", department="Facilities", owner_id="user_4", created_by="user_4", status="open"),
        WorkOrder(title="Install software", department="IT", owner_id="user_5", created_by="user_5", status="open"),
        WorkOrder(title="Fix door", department="Facilities", owner_id="user_6", created_by="user_2", status="open"),
        WorkOrder(title="Update servers", department="IT", owner_id="user_11", created_by="user_11", status="open"),
        WorkOrder(title="Paint walls", department="Facilities", owner_id="user_12", created_by="user_12", status="open"),
    ]
    
    for order in test_orders:
        db.add(order)
    
    db.commit()
    
    return JSONResponse({"status": "success", "count": len(test_orders)})

@app.get("/")
async def root():
    """Health check"""
    return {"status": "healthy", "app": "workorders", "filters": "enabled"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)