-- PostgreSQL initialization for Sancta Nexus
-- Runs automatically on first container start via docker-entrypoint-initdb.d

-- UUID generation (used as primary keys throughout the application)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Full-text search with trigram similarity
-- Used by journal search (ILIKE queries benefit from pg_trgm index)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Case-insensitive text type (login/email lookups)
CREATE EXTENSION IF NOT EXISTS "citext";
