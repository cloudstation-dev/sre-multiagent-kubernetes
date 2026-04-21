### STAGE 1: base image
ARG DOCKER_REGISTRY=ghcr.io
ARG VERSION=0.9.0-beta3
FROM $DOCKER_REGISTRY/kagent-dev/kagent/kagent-adk:$VERSION

WORKDIR /app

COPY  coordinator/ coordinator/
COPY  pyproject.toml pyproject.toml
COPY  README.md README.md
COPY  .python-version .python-version

CMD ["coordinator"]
