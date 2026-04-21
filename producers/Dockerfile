FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* requirements.txt ./

# Install dependencies (no project install — we run from source)
RUN uv sync --frozen --no-install-project 2>/dev/null || uv pip install --system -r requirements.txt

COPY . .

CMD ["python", "main.py"]
