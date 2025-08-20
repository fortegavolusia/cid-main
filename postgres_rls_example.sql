-- Postgres RLS Example for CID Resource Filters
-- This shows how to translate CID policies to row-level security

-- Enable RLS on work_orders table
ALTER TABLE public.work_orders ENABLE ROW LEVEL SECURITY;

-- Policy for read access combining department and ownership filters
-- Matches the CID policy: department OR ownership
CREATE POLICY wo_read ON public.work_orders
FOR SELECT USING (
  -- Department filter: user can see their department's orders
  department = current_setting('request.jwt.claims', true)::jsonb -> 'cid' ->> 'department'
  OR 
  -- Ownership filter: user can see orders they own
  owner_id::text = (auth.uid())::text
);

-- Policy for update access with same filters
CREATE POLICY wo_update ON public.work_orders
FOR UPDATE USING (
  department = current_setting('request.jwt.claims', true)::jsonb -> 'cid' ->> 'department'
  OR 
  owner_id::text = (auth.uid())::text
);

-- For Supabase specifically, the JWT claims are automatically available
-- through auth.uid() and auth.jwt() functions

-- Example with custom attribute filter
CREATE POLICY wo_custom ON public.work_orders
FOR SELECT USING (
  -- Custom field matching user attribute
  assigned_to::text = current_setting('request.jwt.claims', true)::jsonb -> 'cid' ->> 'uid'
);

-- Combined policy with multiple clauses (OR between them)
CREATE POLICY wo_combined ON public.work_orders
FOR ALL USING (
  -- Clause 1: Department match
  department = current_setting('request.jwt.claims', true)::jsonb -> 'cid' ->> 'department'
  OR
  -- Clause 2: Ownership match
  owner_id::text = (auth.uid())::text
  OR
  -- Clause 3: Assignment match
  assigned_to::text = current_setting('request.jwt.claims', true)::jsonb -> 'cid' ->> 'uid'
);

-- Grant usage to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, UPDATE ON public.work_orders TO authenticated;

-- Note: In production, hierarchy filters would require a separate function
-- to resolve user relationships, like:
/*
CREATE OR REPLACE FUNCTION get_subordinates(user_id text)
RETURNS SETOF text AS $$
BEGIN
  RETURN QUERY
  SELECT subordinate_id FROM org_hierarchy 
  WHERE manager_id = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Then use in policy:
CREATE POLICY wo_hierarchy ON public.work_orders
FOR SELECT USING (
  created_by = ANY(SELECT get_subordinates(auth.uid()::text))
);
*/