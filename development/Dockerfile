ARG python_ver=3.7
FROM python:${python_ver}

ARG nautobot_ver=1.0.0b3
ENV PYTHONUNBUFFERED=1 \
    PATH="/root/.poetry/bin:$PATH" \
    NAUTOBOT_CONFIG="/source/development/nautobot_config.py"

RUN mkdir -p /opt

# Upgrade pip and install poetry as well as configure poetry
RUN pip install --upgrade pip\
    && pip install poetry \
    && poetry config virtualenvs.create false

# -------------------------------------------------------------------------------------
# Install Nautobot NetBox Importer Plugin
# -------------------------------------------------------------------------------------
WORKDIR /source

# Copy in only pyproject.toml/poetry.lock to help with caching this layer if no updates to dependencies
COPY poetry.lock pyproject.toml /source/
# --no-root declares not to install the project package since we're wanting to take advantage of caching dependency installation
# and the project is copied in and installed after this step
RUN poetry install --no-interaction --no-ansi --no-root

# Copy in the rest of the source code and install local Nautobot plugin
COPY . /source
RUN poetry install --no-interaction --no-ansi
