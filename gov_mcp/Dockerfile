# Dockerfile for GOV CA Dataset MCP Server
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY gov_mcp/ ./gov_mcp/
COPY pyproject.toml .

# Install the package
RUN pip install --no-cache-dir -e .

# Expose the default SSE port
EXPOSE 8002

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the server with SSE transport
CMD ["python", "-m", "gov_mcp.server", "--sse", "--host", "0.0.0.0", "--port", "8002"]
