-- Initial PostgreSQL schema for the Humane Connection application.
-- This migration creates the shared database foundation for accounts,
-- profiles, growth-plan content, and knowledge-base metadata.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_name TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    access_level TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT accounts_access_level_check
        CHECK (access_level IN ('admin', 'user', 'read_only'))
);

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    company_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profile_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    content TEXT NOT NULL,
    source_filename TEXT,
    source_file_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT profile_documents_document_type_check
        CHECK (document_type IN ('personality', 'job_functions', 'observations'))
);

CREATE UNIQUE INDEX IF NOT EXISTS profile_documents_profile_type_idx
    ON profile_documents(profile_id, document_type);

CREATE TABLE IF NOT EXISTS observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    area TEXT NOT NULL,
    observation TEXT NOT NULL,
    impact TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS observations_profile_position_idx
    ON observations(profile_id, position);

CREATE TABLE IF NOT EXISTS growth_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    used_humane_connection BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS growth_plans_profile_updated_idx
    ON growth_plans(profile_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_base_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uploaded_by_account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    filename TEXT NOT NULL UNIQUE,
    file_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS knowledge_base_sources_active_idx
    ON knowledge_base_sources(is_active);

CREATE INDEX IF NOT EXISTS knowledge_base_sources_sha256_idx
    ON knowledge_base_sources(sha256);

CREATE TABLE IF NOT EXISTS knowledge_base_index_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state TEXT NOT NULL,
    index_method TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    source_files_seen INTEGER NOT NULL DEFAULT 0,
    source_files_indexed INTEGER NOT NULL DEFAULT 0,
    chunks INTEGER NOT NULL DEFAULT 0,
    manifest JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS knowledge_base_index_runs_started_idx
    ON knowledge_base_index_runs(started_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_base_index_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    index_run_id UUID NOT NULL REFERENCES knowledge_base_index_runs(id) ON DELETE CASCADE,
    source_filename TEXT NOT NULL,
    error_message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS knowledge_base_index_errors_run_idx
    ON knowledge_base_index_errors(index_run_id);

DROP TRIGGER IF EXISTS accounts_set_updated_at ON accounts;
CREATE TRIGGER accounts_set_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS profiles_set_updated_at ON profiles;
CREATE TRIGGER profiles_set_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS profile_documents_set_updated_at ON profile_documents;
CREATE TRIGGER profile_documents_set_updated_at
    BEFORE UPDATE ON profile_documents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS observations_set_updated_at ON observations;
CREATE TRIGGER observations_set_updated_at
    BEFORE UPDATE ON observations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS growth_plans_set_updated_at ON growth_plans;
CREATE TRIGGER growth_plans_set_updated_at
    BEFORE UPDATE ON growth_plans
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS knowledge_base_sources_set_updated_at ON knowledge_base_sources;
CREATE TRIGGER knowledge_base_sources_set_updated_at
    BEFORE UPDATE ON knowledge_base_sources
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
