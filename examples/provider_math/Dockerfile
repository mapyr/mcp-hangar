FROM python:3.11-slim

WORKDIR /app

# Install MCP SDK
RUN pip install --no-cache-dir mcp

# Copy provider code
COPY server.py /app/server.py
COPY __init__.py /app/__init__.py

# Run the provider
CMD ["python", "server.py"]
