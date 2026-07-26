# See Project Description
Docker Development

Create a local `.env` file from `.env.example` and set the PostgreSQL values.
The `.env` file is ignored by Git and should contain your local database password.

Run the Streamlit app and PostgreSQL together:

```bash
docker compose up --build
```

Open the app:

```text
http://localhost:8501
```

The Dockerized app connects to PostgreSQL through the Compose service name
`postgres`.

## Local App With Docker PostgreSQL

If you want to run the Streamlit app directly on your machine while only
PostgreSQL runs in Docker, keep `POSTGRES_HOST=localhost` in `.env` and start the
database:

```bash
docker compose up -d postgres
```

Verify the Streamlit app can connect:

```bash
uv run python scripts/db_smoke_test.py
```

Apply the initial database schema:

```bash
uv run python scripts/db_migrate.py
```

Verify the expected schema tables exist:

```bash
uv run python scripts/db_schema_check.py
```
