-- PostgreSQL initialisation script
-- Runs automatically when the Docker container first starts
-- (mounted as /docker-entrypoint-initdb.d/init.sql)

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for text similarity search

-- Performance tuning for pgvector workloads
-- Increase maintenance_work_mem for faster HNSW index builds
ALTER SYSTEM SET maintenance_work_mem = '256MB';
SELECT pg_reload_conf();
