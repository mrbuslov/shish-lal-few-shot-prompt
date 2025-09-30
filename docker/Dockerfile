FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only requirements first for better caching
# Application code will be mounted as volume for development

# Create necessary directories
RUN mkdir -p /app/user_reports_files
RUN mkdir -p /app/src
RUN mkdir -p /app/templates
RUN mkdir -p /app/static
RUN mkdir -p /app/files

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health_check || exit 1

# Run the FastAPI application with reload for development
CMD ["python", "-m", "uvicorn", "src.fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
