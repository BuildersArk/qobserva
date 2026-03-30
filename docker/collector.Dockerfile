# Use Python 3.12 for best compatibility with all SDKs
# - Supports Qiskit, Braket, Cirq, PennyLane, D-Wave, pyQuil
# - Python 3.13+ breaks Braket (Pydantic v1 limitation)
# - Python 3.13+ breaks pyQuil (PyO3 0.20.3 limitation)
FROM python:3.12-slim

WORKDIR /app

# Copy required directories
COPY schema /app/schema
COPY spec /app/spec
COPY packages/qobserva_collector /app/packages/qobserva_collector
COPY packages/qobserva_agent /app/packages/qobserva_agent

# Install packages and curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /app/packages/qobserva_agent -e /app/packages/qobserva_collector

EXPOSE 8080

# Health check (using curl - more reliable, no Python import needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/v1/health || exit 1

CMD ["uvicorn", "qobserva_collector.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
