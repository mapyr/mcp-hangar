FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY pyproject.toml /app/
COPY mcp_hangar/ /app/mcp_hangar/
COPY examples/ /app/examples/
COPY README.md /app/

# Install the package with uv
RUN uv pip install --system .

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_LOG_LEVEL=INFO

# Expose port (if needed for future HTTP interface)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the registry server
CMD ["python", "-m", "mcp_hangar.server"]
