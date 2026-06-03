# Dockerfile
# ══════════════════════════════════════════════════════
# WHAT THIS FILE DOES:
# Packages your FastAPI app + all dependencies
# into a single Docker image that runs anywhere
# ══════════════════════════════════════════════════════

# Step 1: Start from official Python image
# python:3.11-slim = Python 3.11 on minimal Linux (smaller image)
FROM python:3.11-slim

# Step 2: Set working directory inside container
# All commands run from here. Like cd /app
WORKDIR /app

# Step 3: Install system dependencies needed by psycopg2
# (PostgreSQL client libraries)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Step 4: Copy requirements FIRST — BEFORE copying code
# WHY: Docker caches each step as a "layer"
# If requirements.txt doesn't change → Docker reuses cached layer
# → pip install is SKIPPED on next build (much faster!)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy your application code
# NOW we copy code — changes here don't invalidate the pip install layer
COPY . .

# Step 6: Expose the port your app listens on
# This is documentation — tells Docker which port to open
EXPOSE 8000

# Step 7: Health check — Docker checks if app is alive
# Every 30s, runs curl. If /health returns 200 → healthy
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Step 8: Command to run when container starts
# gunicorn = production process manager
# -k uvicorn.workers.UvicornWorker = use async Uvicorn workers
# -w 2 = 2 worker processes
# app.main:app = folder.file:FastAPI_variable
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# For production with multiple workers:
# CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "--bind", "0.0.0.0:8000"]