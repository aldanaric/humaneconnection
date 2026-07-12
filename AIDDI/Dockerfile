FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY .python-version pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev

# Install Chromium and the Linux libraries required by Playwright.
RUN uv run playwright install --with-deps chromium \
    && chmod -R 755 /ms-playwright

COPY . .

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
