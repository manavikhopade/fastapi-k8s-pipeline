# 1. Start from a small, official Python 3.12 image
FROM python:3.12-slim

# Patch OS packages to fix known vulnerabilities (util-linux CVE-2026-53615)
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# 2. Bring in the `uv` tool by copying it from its official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 3. Do all work inside /app in the container
WORKDIR /app

# 4. Copy ONLY the dependency files first (so Docker can cache the install step)
COPY pyproject.toml uv.lock ./

# 5. Install production dependencies, exact versions from the lockfile
RUN uv sync --frozen --no-dev --no-install-project

# 6. Put the virtual environment on the PATH so its tools (uvicorn) run directly
ENV PATH="/app/.venv/bin:$PATH"

# 7. Now copy the application code
COPY app ./app

# 8. Help Python find the "app" package
ENV PYTHONPATH=/app

# 9. Document that the app listens on port 8000
EXPOSE 8000

# 10. Start the web server, bound to 0.0.0.0 so it's reachable from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
