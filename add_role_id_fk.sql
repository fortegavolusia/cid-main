-- Agregar foreign key constraint para rol_id
ALTER TABLE cids.app_role_mappings 
ADD CONSTRAINT app_role_mappings_rol_id_fkey 
FOREIGN KEY (rol_id) 
REFERENCES cids.role_metadata(role_id) 
ON DELETE CASCADE;