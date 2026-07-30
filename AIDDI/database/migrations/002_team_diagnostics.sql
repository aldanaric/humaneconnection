-- Team Diagnostics schema.
-- Teams are owned by accounts. Members are linked profiles.
-- Personality and job-function inputs stay on profile_documents.
-- Generated packets are stored in team_diagnostic_reports (like growth_plans).

CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    company_info TEXT NOT NULL DEFAULT '',
    team_info TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT teams_account_name_unique UNIQUE (account_id, name)
);

CREATE INDEX IF NOT EXISTS teams_account_updated_idx
    ON teams(account_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT team_members_team_profile_unique UNIQUE (team_id, profile_id)
);

CREATE INDEX IF NOT EXISTS team_members_team_position_idx
    ON team_members(team_id, position);

CREATE INDEX IF NOT EXISTS team_members_profile_idx
    ON team_members(profile_id);

CREATE TABLE IF NOT EXISTS team_diagnostic_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    prompt_template_name TEXT NOT NULL DEFAULT 'default',
    audience TEXT NOT NULL DEFAULT 'Facilitator',
    requested_outputs JSONB NOT NULL DEFAULT '[]'::jsonb,
    used_humane_connection BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT team_diagnostic_reports_audience_check
        CHECK (audience IN ('Facilitator', 'Manager', 'Peer'))
);

CREATE INDEX IF NOT EXISTS team_diagnostic_reports_team_updated_idx
    ON team_diagnostic_reports(team_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS team_diagnostic_reports_account_updated_idx
    ON team_diagnostic_reports(account_id, updated_at DESC);

DROP TRIGGER IF EXISTS teams_set_updated_at ON teams;
CREATE TRIGGER teams_set_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS team_members_set_updated_at ON team_members;
CREATE TRIGGER team_members_set_updated_at
    BEFORE UPDATE ON team_members
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS team_diagnostic_reports_set_updated_at ON team_diagnostic_reports;
CREATE TRIGGER team_diagnostic_reports_set_updated_at
    BEFORE UPDATE ON team_diagnostic_reports
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
