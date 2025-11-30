-- =============================================================================
-- FaceLogix Database Initialization Script
-- PostgreSQL initialization for pgvector-enabled face recognition database
-- =============================================================================
-- This script runs automatically when the PostgreSQL container starts
-- for the first time. It creates required extensions and optional settings.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Enable Required Extensions
-- -----------------------------------------------------------------------------

-- UUID generation for primary keys
-- Provides uuid_generate_v4() function for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions
-- Provides gen_random_uuid(), crypt(), gen_salt() for password hashing
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Vector similarity search for face embeddings
-- Enables storing and querying 512-dimensional face embedding vectors
CREATE EXTENSION IF NOT EXISTS "vector";

-- -----------------------------------------------------------------------------
-- Optional: Performance and Monitoring Extensions
-- -----------------------------------------------------------------------------

-- Statistics collection for query optimization (usually enabled by default)
-- CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- -----------------------------------------------------------------------------
-- Optional: Create Application User with Limited Privileges
-- Uncomment and modify for production environments
-- -----------------------------------------------------------------------------
-- DO $$
-- BEGIN
--     -- Create application user if not exists
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'facelogix_app') THEN
--         CREATE USER facelogix_app WITH PASSWORD 'app_password_change_me';
--     END IF;
-- END
-- $$;

-- Grant necessary privileges to application user
-- GRANT CONNECT ON DATABASE facelogix TO facelogix_app;
-- GRANT USAGE ON SCHEMA public TO facelogix_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO facelogix_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO facelogix_app;

-- Grant privileges on future tables
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO facelogix_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO facelogix_app;

-- -----------------------------------------------------------------------------
-- Performance Settings (adjust based on your server resources)
-- These can also be set in postgresql.conf
-- -----------------------------------------------------------------------------

-- Set default index method for vector columns to ivfflat for faster similarity search
-- Note: You'll want to create specific indexes after data is loaded
-- Example: CREATE INDEX ON face_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- -----------------------------------------------------------------------------
-- Verify Extensions
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    ext_record RECORD;
BEGIN
    RAISE NOTICE '=== Installed Extensions ===';
    FOR ext_record IN 
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname IN ('uuid-ossp', 'pgcrypto', 'vector')
        ORDER BY extname
    LOOP
        RAISE NOTICE '  % version %', ext_record.extname, ext_record.extversion;
    END LOOP;
    RAISE NOTICE '============================';
END
$$;

-- -----------------------------------------------------------------------------
-- Seed Data: Default Organization and Admin User
-- -----------------------------------------------------------------------------
-- Note: These are created after Alembic migrations run. The backend will
-- check and create these if they don't exist on startup.
-- Password hash below is for 'admin123' using bcrypt.
-- -----------------------------------------------------------------------------

-- This section is commented out because tables are created by Alembic.
-- Uncomment if you want to pre-seed data (run after migrations).

/*
-- Create default organization
INSERT INTO orgs (id, name, slug, settings, created_at, updated_at)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Demo Organization',
    'demo-org',
    '{"work_start_time": "09:00", "work_end_time": "18:00", "late_threshold_minutes": 15, "timezone": "UTC"}',
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Create admin user (password: admin123)
-- Hash generated with: python -c "import bcrypt; print(bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode())"
INSERT INTO users (id, org_id, email, password_hash, full_name, employee_id, role, is_active, created_at, updated_at)
VALUES (
    'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'admin@facelogix.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G7xeqGmhKqGqGe',
    'System Administrator',
    'ADMIN001',
    'admin',
    true,
    NOW(),
    NOW()
) ON CONFLICT (id) DO NOTHING;
*/

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'FaceLogix database initialization completed successfully.';
    RAISE NOTICE 'Run Alembic migrations and seed script to create tables and default user.';
END
$$;
