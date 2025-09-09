FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies directly (no requirements.txt)
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic \
    httpx \
    python-dotenv \
    jinja2 \
    authlib \
    python-jose[cryptography] \
    psycopg2-binary \
    supabase

# Copy application code
COPY . .

# Create data directory for JSON persistence
RUN mkdir -p /app/infra/data/app_data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]