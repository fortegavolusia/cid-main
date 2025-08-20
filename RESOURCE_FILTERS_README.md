# CID Resource Filters v1

Resource-level permissions that apps enforce with minimal code.

## How It Works

1. **Publish**: Admin configures filters in CID role → clicks Publish → CID compiles to JSON policy
2. **Push**: CID pushes policy to app webhook with HMAC signature
3. **Cache**: App stores (role,version) → policy in memory
4. **Enforce**: App reads {role,ver} from JWT, applies cached policy to queries

## Example Flow

```bash
# 1. Publish role with filters
POST /roles/workorders/DPW_EDITOR/publish

# 2. CID pushes to app
POST https://app/cid/policies
Body: {"app":"workorders","policies":[{...}]}
Header: X-CID-Signature: sha256=<hmac>

# 3. JWT contains only reference
{"cid":{"apps":[{"app":"workorders","roles":[{"name":"DPW_EDITOR","ver":1}]}]}}

# 4. App enforces on queries
GET /work-orders → filtered by department OR ownership
```

## Usage

```python
# In your app
filtered_query = enforce(
    query, "work_order", "read", 
    user_ctx, [policy], colmap
)
```

## Optional RLS

```sql
CREATE POLICY wo_read ON work_orders FOR SELECT USING (
  department = current_setting('request.jwt.claims')::jsonb->'cid'->>'department'
  OR owner_id = auth.uid()
);
```