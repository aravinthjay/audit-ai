-- Local PostgreSQL setup for Skeptic Engine.
-- Use pgAdmin Query Tool while connected to the default "postgres" database.

-- Step 1: create or update the local login role.
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'skeptic'
   ) THEN
      CREATE ROLE skeptic LOGIN PASSWORD 'skeptic_dev_password';
   ELSE
      ALTER ROLE skeptic WITH LOGIN PASSWORD 'skeptic_dev_password';
   END IF;
END
$$;

-- Step 2: run this statement separately if "skeptic_engine" is not already
-- listed under Databases in pgAdmin. CREATE DATABASE cannot be run inside
-- another transaction block.
CREATE DATABASE skeptic_engine OWNER skeptic;

-- Step 3: after creating the database, right-click "skeptic_engine" in pgAdmin,
-- open Query Tool for that database, and run these grants.
GRANT ALL PRIVILEGES ON DATABASE skeptic_engine TO skeptic;
GRANT ALL ON SCHEMA public TO skeptic;
