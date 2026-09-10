# test.Dockerfile
# This Dockerfile is used to test OneCrawler across multiple Python versions (3.10 - 3.13)
# It uses the deadsnakes PPA to provide multiple Python versions on an Ubuntu base.

FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install basic dependencies and add the deadsnakes PPA
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    git \
    build-essential \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update

# 2. Install all target Python versions and their venv modules
RUN apt-get install -y \
    python3.10 python3.10-venv python3.10-dev \
    python3.11 python3.11-venv python3.11-dev \
    python3.12 python3.12-venv python3.12-dev \
    python3.13 python3.13-venv python3.13-dev \
    python3.14 python3.14-venv python3.14-dev

# 3. Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 4. Set up workspace
WORKDIR /app
COPY . .

# 5. Install Playwright system dependencies
# This ensures that even if tests use browsers, they won't fail due to missing libraries
RUN apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2

# 6. Create a container-specific test script
# This script is similar to version_test.sh but specifically targets system-installed pythons
RUN echo '#!/bin/bash\n\
VERSIONS=("3.10" "3.11" "3.12" "3.13" "3.14")\n\
ALL_PASSED=true\n\
\n\
for VER in "${VERSIONS[@]}"; do\n\
    echo "--------------------------------------------------"\n\
    echo "🧪 Testing Python $VER..."\n\
    VENV_NAME="venv-$VER"\n\
    \n\
    uv venv "$VENV_NAME" --python "$VER" &> /dev/null\n\
    uv pip install --python "$VENV_NAME/bin/python" -e ".[dev]" &> /dev/null\n\
    # Install playwright browsers (chromium) for this venv\n\
    "$VENV_NAME/bin/playwright" install chromium &> /dev/null\n\
    \n\
    if "$VENV_NAME/bin/pytest"; then\n\
        echo "✅ Python $VER tests passed!"\n\
    else\n\
        echo "❌ Python $VER tests failed!"\n\
        ALL_PASSED=false\n\
    fi\n\
    rm -rf "$VENV_NAME"\n\
done\n\
\n\
if [ "$ALL_PASSED" = true ]; then\n\
    echo "🎉 ALL VERSIONS PASSED!"\n\
    exit 0\n\
else\n\
    echo "❌ SOME VERSIONS FAILED!"\n\
    exit 1\n\
fi' > /app/run_all_tests.sh && chmod +x /app/run_all_tests.sh

# Run the test runner script by default
CMD ["/app/run_all_tests.sh"]


# How to run
# sudo docker build -t onecrawler-test -f test.Dockerfile .
# sudo docker run --rm onecrawler-test
