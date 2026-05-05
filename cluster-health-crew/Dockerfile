### Cluster Health Crew - CrewAI Agent
# Reproducible build using kagent-crewai from PyPI
# Build from anywhere:
#   docker build -t cluster-health-crew:v2 .

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy project files
COPY src/ src/
COPY pyproject.toml .
COPY README.md .
COPY .python-version .

# Create venv and install dependencies from PyPI
RUN uv venv && uv pip install -e . && uv cache clean

# Set environment variables
ENV PORT=8080
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "-m", "cluster_health_crew.main"]
