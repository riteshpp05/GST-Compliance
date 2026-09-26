# UC15 GST Compliance Intelligence & Resolution Agent — Production Dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Final Production Stage ---
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user
RUN groupadd -g 999 appgroup && \
    useradd -r -u 999 -g appgroup appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . /app

# Set ownership
RUN chown -R appuser:appgroup /app

USER appuser

ENV PORT=8000
ENV APP_ENV=production
ENV LOG_LEVEL=INFO

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready')" || exit 1

CMD ["python", "main.py", "--ui"]
