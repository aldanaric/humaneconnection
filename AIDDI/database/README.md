# Database Development Guide

This folder contains the shared PostgreSQL schema foundation for AIDDI.

## Current Structure

```text
database/
└── migrations/
    └── 001_initial_schema.sql
    └── TEMPLATE_new_section.sql.example
```

## Running Migrations

Start PostgreSQL first:

```bash
docker compose up -d postgres
```

Apply all pending migrations:

```bash
uv run python scripts/db_migrate.py
```

Verify the expected tables exist:

```bash
uv run python scripts/db_schema_check.py
```

## Adding a New Section

When a teammate needs database support for a new app section:

1. Create a new migration in `database/migrations/`.
2. Copy `database/migrations/TEMPLATE_new_section.sql.example`.
3. Use the next migration number, for example `002_team_diagnostics.sql`.
4. Add only the tables, indexes, and constraints needed for that section.
5. Keep foreign keys connected to the shared core tables when appropriate.
6. Add repository methods under `repositories/` for application code to use.

There is also a repository starter file at:

```text
repositories/database_repository_template.py.example
```

## Core Tables

- `accounts`: Login accounts and access levels.
- `profiles`: People/person profiles owned by an account.
- `profile_documents`: Profile input documents stored as text.
- `observations`: Structured profile observations.
- `growth_plans`: Saved growth plan outputs.
- `knowledge_base_sources`: Metadata for uploaded knowledge-base files.
- `knowledge_base_index_runs`: Knowledge-base rebuild history.
- `knowledge_base_index_errors`: File-level errors from a rebuild.

## Naming Conventions

- Use plural snake_case table names.
- Use UUID primary keys named `id`.
- Use `created_at` and `updated_at` on mutable tables.
- Use foreign keys named after the parent table, such as `account_id` or `profile_id`.
- Store large generated app text in `TEXT` columns.
- Store uploaded knowledge-base files on disk and keep their metadata in PostgreSQL.

## Access Levels

The `accounts.access_level` column should use one of:

```text
admin
user
read_only
```

This matches `models/access_level.py`.

## Notes

The current Streamlit features may still use file-based repositories while the team migrates section by section. New database-backed work should use the shared connection helpers in `services/database.py` and should keep database code behind repository/service functions.
