# syntax=docker/dockerfile:1
# Lanvex Core: NetBox with Lanvex's branding and single sign-on. Build from the repository root:
#
#   docker build -f lanvex/Dockerfile -t lanvex-core .
#
# One image, three roles (see docker-entrypoint.sh): core (the web application), worker (background
# jobs) and manage (any manage.py command).

# Fully qualified, so Podman on Fedora/RHEL (short-name-mode enforcing) builds without asking.
ARG PYTHON_IMAGE=docker.io/library/python:3.13-slim

# ---- dependencies and documentation -------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS build
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
COPY . .
# NetBox serves its documentation from the static files; build it like upgrade.sh does.
RUN /opt/venv/bin/zensical build

# ---- runtime -----------------------------------------------------------------------------------
FROM ${PYTHON_IMAGE}
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --gid 1000 lanvexcore \
 && useradd --uid 1000 --gid lanvexcore --no-create-home --home-dir /opt/lanvex-core --shell /usr/sbin/nologin lanvexcore
COPY --from=build /opt/venv /opt/venv
COPY --from=build /src /opt/lanvex-core
RUN mkdir -p /opt/lanvex-core/netbox/static /opt/lanvex-core/netbox/media /opt/lanvex-core/netbox/reports /opt/lanvex-core/netbox/scripts \
 && chown -R lanvexcore:lanvexcore /opt/lanvex-core/netbox/static /opt/lanvex-core/netbox/media \
      /opt/lanvex-core/netbox/reports /opt/lanvex-core/netbox/scripts
ENV PATH=/opt/venv/bin:$PATH \
    NETBOX_CONFIGURATION=lanvex_configuration \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
USER lanvexcore
WORKDIR /opt/lanvex-core/netbox
EXPOSE 8080
# The health check (lanvex/healthcheck.py, for the web application or the worker) is in Lanvex's
# docker-compose.yml: Podman builds OCI images, which cannot carry one and warn about it on every build.
# Through sh, so the script works even if an unpacked archive lost its execute permission.
ENTRYPOINT ["/bin/sh", "/opt/lanvex-core/lanvex/docker-entrypoint.sh"]
CMD ["core"]
