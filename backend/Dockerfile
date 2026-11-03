FROM ubuntu:latest

WORKDIR /src

COPY install_system_requirements.sh .
RUN bash ./install_system_requirements.sh

# Install Poetry
RUN pip install --break-system-packages --ignore-installed poetry==2.2.1

# Configure Poetry: no venv inside container, no interaction
ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1

# Copy dependency files first (layer cache optimisation)
COPY pyproject.toml poetry.lock ./

# Install dependencies
# Set BUILD_ENV=dev to also install dev dependencies (e.g. for running tests)
ARG BUILD_ENV=prod
RUN if [ "$BUILD_ENV" = "dev" ]; then \
        poetry install --no-root; \
    else \
        poetry install --only main --no-root; \
    fi

COPY . .

RUN chmod +x start.sh

CMD ["./start.sh"]
