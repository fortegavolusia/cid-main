-- Script para eliminar la tabla cids.roles y sus dependencias
-- ADVERTENCIA: Esto eliminará datos. Asegúrate de hacer un respaldo primero.

-- Opción 1: Eliminar con CASCADE (eliminará también la tabla permissions)
-- Esto es la forma más rápida pero eliminará TODAS las tablas dependientes
DROP TABLE IF EXISTS cids.roles CASCADE;

-- Opción 2: Eliminar solo la constraint y luego la tabla (preserva la tabla permissions)
-- Descomenta las siguientes líneas si prefieres esta opción:
/*
-- Primero eliminar la foreign key constraint de la tabla permissions
ALTER TABLE cids.permissions DROP CONSTRAINT IF EXISTS permissions_role_id_fkey;

-- Luego eliminar la tabla roles
DROP TABLE IF EXISTS cids.roles;
*/

-- Opción 3: Hacer backup primero, luego eliminar y recrear
-- Ejecuta estos comandos en la terminal antes de correr este script:
/*
-- Backup de datos
pg_dump -h localhost -p 54322 -U postgres -t cids.roles -t cids.permissions postgres > roles_backup.sql

-- Luego ejecuta este script con la Opción 1
*/