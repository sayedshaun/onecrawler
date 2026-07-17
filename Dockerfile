### Builder stage — compiles/installs onecrawler and downloads the Chromium
### browser binary. Nothing from here lands in the final image except the
### installed venv and the browser files copied explicitly below.
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# build-essential is only needed to compile C-extension dependencies that
# don't ship a prebuilt wheel for this Python version; it never reaches
# the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install into an isolated venv so it can be copied wholesale into the
# final stage without dragging along build tooling or pip's cache.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the full library source before installing, so setuptools'
# package auto-discovery actually finds the onecrawler package
COPY . .

RUN pip install --no-cache-dir .

# Download only the Chromium browser bundle here; its OS-level shared-lib
# dependencies are installed separately in the final stage via
# `playwright install-deps`, so they aren't duplicated across stages.
RUN playwright install chromium


### Final stage — slim runtime image: no compiler, no repo source, no
### package-manager caches. Just the installed venv, the browser binary,
### and the OS libraries Chromium actually needs to run headless.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /ms-playwright /ms-playwright

# Installs the OS shared libraries Chromium needs at runtime, without
# re-downloading the browser binary itself (already copied in above).
RUN playwright install-deps chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Optional: Set a non-root user for security
# This is recommended for production crawlers
RUN useradd -m onecrawler && chown -R onecrawler:onecrawler /app
USER onecrawler

# Default command: show help/version or run a script if provided
CMD ["python", "-m", "onecrawler"]
