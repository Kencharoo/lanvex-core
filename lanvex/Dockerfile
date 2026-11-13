# syntax=docker/dockerfile:1
# Lanvex Core: NetBox with Lanvex's branding and single sign-on. Build from the repository root:
#
#   docker build -f lanvex/Dockerfile -t lanvex-core .
#
# One image, three roles (see docker-entrypoint.sh): core (the web application), worker (background
# jobs) and manage (any manage.py command).

ARG PYTHON_IMAGE=python:3.13-slim

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
 && groupadd --system --gid 1000 lanvexcore \
 && useradd --system --uid 1000 --gid lanvexcore --home /opt/lanvex-core --shell /usr/sbin/nologin lanvexcore
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
HEALTHCHECK --interval=15s --timeout=5s --start-period=600s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/core/login/', timeout=4).status == 200 else 1)"
ENTRYPOINT ["/opt/lanvex-core/lanvex/docker-entrypoint.sh"]
CMD ["core"]
