	
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

COPY .python-version pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]