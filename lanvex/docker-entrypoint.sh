#!/bin/sh
# Lanvex Core container roles:
#   core     prepare the database and static files like NetBox's upgrade.sh, set up Lanvex's
#            service account, then serve the application on port 8080
#   worker   run background jobs once the database is migrated
#   manage   run a manage.py command, e.g. "manage nbshell"
set -eu
cd /opt/lanvex-core/netbox

wait_for_database() {
  python - <<'PY'
import os, sys, time
import psycopg
for attempt in range(60):
    try:
        psycopg.connect(
            host=os.environ.get('LANVEX_CORE_DB_HOST', 'core-db'), port=os.environ.get('LANVEX_CORE_DB_PORT') or 5432,
            dbname=os.environ.get('LANVEX_CORE_DB_NAME', 'lanvex_core'), user=os.environ.get('LANVEX_CORE_DB_USER', 'lanvex_core'),
            password=os.environ['LANVEX_CORE_DB_PASSWORD'], connect_timeout=3,
        ).close()
        sys.exit(0)
    except psycopg.OperationalError as e:
        print(f'Waiting for the database: {e}'.strip(), flush=True)
        time.sleep(2)
sys.exit('The database did not become reachable within two minutes.')
PY
}

role=${1:-core}
case "$role" in
  core)
    wait_for_database
    echo "Applying database migrations (the first start takes several minutes)..."
    python manage.py migrate --no-input
    python manage.py trace_paths --no-input
    python manage.py rebuild_config_context_cache
    python manage.py remove_stale_contenttypes --no-input
    python manage.py reindex --lazy
    python manage.py clearsessions
    python manage.py collectstatic --no-input -v 0
    python manage.py lanvex_init
    # No control socket: nothing uses gunicorn's control interface, and the home directory is read-only.
    exec gunicorn --bind 0.0.0.0:8080 --workers "${LANVEX_CORE_WORKERS:-3}" --threads 3 --timeout 120 \
      --no-control-socket \
      --max-requests 5000 --max-requests-jitter 500 --access-logfile - netbox.wsgi
    ;;
  worker)
    wait_for_database
    until python manage.py migrate --check >/dev/null 2>&1; do
      echo "Waiting for the core container to finish migrating the database..."
      sleep 10
    done
    exec python manage.py rqworker
    ;;
  manage)
    shift
    exec python manage.py "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
