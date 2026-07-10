# Use an official Python slim image as the base
FROM python:3.14-slim

# Set environment variables
# 1. Prevent Python from writing .pyc files
# 2. Ensure stdout/stderr are flushed immediately
# 3. Tell Playwright where to find the browsers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Set work directory
WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the full framework source before installing, so setuptools'
# package auto-discovery actually finds the onecrawler package
COPY . .

# Install the framework and its dependencies
# We include [genai] extra by default for the Docker image
RUN pip install --no-cache-dir .[genai]

# Install Playwright browsers and their specific system dependencies
# OneCrawler primarily uses Chromium
RUN playwright install chromium --with-deps

# Optional: Set a non-root user for security
# This is recommended for production crawlers
RUN useradd -m onecrawler && chown -R onecrawler:onecrawler /app
USER onecrawler

# Default command: show help/version or run a script if provided
CMD ["python", "-m", "onecrawler"]
