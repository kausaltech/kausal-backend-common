-- Drop every object the current role owns in the public schema, except objects that
-- belong to an extension. The schema itself is kept: on PostgreSQL 15+ it is owned by
-- the database owner (the app role), so DROP OWNED / DROP SCHEMA would take the
-- PostGIS extension with it, and the app role cannot re-create that.
DO $$
DECLARE
    r record;
    owner_oid oid := (SELECT oid FROM pg_roles WHERE rolname = current_user);
BEGIN
    -- Tables (incl. partitioned/foreign) with everything hanging off them
    FOR r IN
        SELECT c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'f') AND c.relowner = owner_oid
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', r.relname);
    END LOOP;
    -- Views and materialized views
    FOR r IN
        SELECT c.relname, c.relkind FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('v', 'm') AND c.relowner = owner_oid
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
    LOOP
        EXECUTE format('DROP %s IF EXISTS public.%I CASCADE',
                       CASE r.relkind WHEN 'm' THEN 'MATERIALIZED VIEW' ELSE 'VIEW' END, r.relname);
    END LOOP;
    -- Stand-alone sequences
    FOR r IN
        SELECT c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S' AND c.relowner = owner_oid
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
    LOOP
        EXECUTE format('DROP SEQUENCE IF EXISTS public.%I CASCADE', r.relname);
    END LOOP;
    -- Functions, procedures, aggregates
    FOR r IN
        SELECT p.oid::regprocedure AS signature, p.prokind FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND p.proowner = owner_oid
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid AND d.deptype = 'e')
    LOOP
        EXECUTE format('DROP %s IF EXISTS %s CASCADE',
                       CASE r.prokind WHEN 'a' THEN 'AGGREGATE' WHEN 'p' THEN 'PROCEDURE' ELSE 'FUNCTION' END, r.signature);
    END LOOP;
    -- Enums, domains, ranges and free-standing composite types (table row types went with their tables)
    FOR r IN
        SELECT t.typname FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typowner = owner_oid
          AND t.typtype IN ('e', 'd', 'r', 'm', 'c')
          AND (t.typtype <> 'c' OR EXISTS (SELECT 1 FROM pg_class c WHERE c.oid = t.typrelid AND c.relkind = 'c'))
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_type'::regclass AND d.objid = t.oid AND d.deptype = 'e')
    LOOP
        EXECUTE format('DROP TYPE IF EXISTS public.%I CASCADE', r.typname);
    END LOOP;
    -- Extensions the app role created itself (e.g. pg_trgm from a migration); migrations re-create them
    FOR r IN
        SELECT e.extname FROM pg_extension e WHERE e.extowner = owner_oid
    LOOP
        EXECUTE format('DROP EXTENSION IF EXISTS %I CASCADE', r.extname);
    END LOOP;
END
$$;
