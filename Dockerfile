FROM mcr.microsoft.com/playwright/python:v1.59.0-noble

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# The Playwright base image already contains Chromium and required OS packages.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 120 --index-url https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p data/snapshots data/logs

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
