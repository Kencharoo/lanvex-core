#!/usr/bin/env bash
# Starts the Lanvex Core image the way Lanvex's docker-compose.yml does, with its own PostgreSQL and
# Redis, and checks what an installation needs: both roles turn healthy, neither logs errors, single
# sign-on works only with the proxy secret, and Lanvex's service token can use the API.
#
#   lanvex/scripts/smoke-image.sh [image; default lanvex-core:ci]
#
# Needs Docker and access to postgres:16-alpine and redis:7-alpine. Removes everything it started.
set -euo pipefail
image=${1:-lanvex-core:ci}
run=lanvex-core-smoke-$$
rand() { LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom 2>/dev/null | head -c "$1" || true; }
db_password=$(rand 32)
proxy_secret=$(rand 48)
token="nbt_$(rand 12).$(rand 40)"

cleanup() {
  docker rm -f "$run-core" "$run-worker" "$run-db" "$run-redis" >/dev/null 2>&1 || true
  docker network rm "$run" >/dev/null 2>&1 || true
}
trap cleanup EXIT

core_env=(
  -e LANVEX_CORE_DB_HOST="$run-db" -e LANVEX_CORE_DB_PASSWORD="$db_password"
  -e LANVEX_CORE_REDIS_HOST="$run-redis"
  -e LANVEX_CORE_SECRET_KEY="$(rand 64)" -e LANVEX_CORE_API_TOKEN_PEPPER="$(rand 64)"
  -e LANVEX_CORE_PROXY_SECRET="$proxy_secret" -e LANVEX_CORE_SERVICE_TOKEN="$token"
  -e LANVEX_CORE_TIME_ZONE=Europe/Berlin -e TZ=Europe/Berlin
)

docker network create "$run" >/dev/null
docker run -d --name "$run-db" --network "$run" \
  -e POSTGRES_DB=lanvex_core -e POSTGRES_USER=lanvex_core -e POSTGRES_PASSWORD="$db_password" postgres:16-alpine >/dev/null
docker run -d --name "$run-redis" --network "$run" redis:7-alpine >/dev/null
docker run -d --name "$run-core" --network "$run" "${core_env[@]}" "$image" >/dev/null
docker run -d --name "$run-worker" --network "$run" "${core_env[@]}" "$image" worker >/dev/null

wait_healthy() {  # wait_healthy CONTAINER MINUTES
  local deadline=$(( $(date +%s) + $2 * 60 )) state
  while :; do
    state=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$1")
    case "$state" in
      healthy) echo "$1: healthy"; return 0 ;;
      unhealthy|exited|dead) break ;;
    esac
    [ "$(date +%s)" -lt "$deadline" ] || { state="still $state after $2 minutes"; break; }
    sleep 5
  done
  echo "$1: $state" >&2
  docker logs --tail 60 "$1" >&2
  return 1
}
status=0
wait_healthy "$run-core" 15 || status=1
wait_healthy "$run-worker" 5 || status=1

for c in "$run-core" "$run-worker"; do
  if docker logs "$c" 2>&1 | grep -E "Traceback|\[ERROR\]|ERROR |Permission denied"; then
    echo "$c logged errors (above)." >&2; status=1
  fi
done
[ $status -eq 0 ] || exit 1

docker exec -i "$run-core" python - "$proxy_secret" "$token" <<'PY'
import json, sys, urllib.error, urllib.request

secret, token = sys.argv[1:3]
base = 'http://127.0.0.1:8080/core'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


open_url = urllib.request.build_opener(NoRedirect).open


def get(path, **headers):
    try:
        with open_url(urllib.request.Request(base + path, headers=headers), timeout=15) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


via_lanvex = {'X-Lanvex-User': 'smoke-admin', 'X-Lanvex-Groups': 'lanvex-admin', 'X-Lanvex-Proxy-Secret': secret}
checks = []
status, body = get('/ipam/prefixes/', **via_lanvex)
checks.append(('signed in through Lanvex', status == 200 and 'Lanvex Core' in body, status))
status, _ = get('/ipam/prefixes/', **{**via_lanvex, 'X-Lanvex-Proxy-Secret': 'x' * 48})
checks.append(('wrong proxy secret refused', status in (302, 403), status))
status, _ = get('/ipam/prefixes/', **{**via_lanvex, 'X-Lanvex-User': 'lanvex-service'})
checks.append(('service account cannot sign in', status in (302, 403), status))
status, body = get('/api/status/', Authorization=f'Bearer {token}', Accept='application/json')
checks.append(('service token reaches the API', status == 200 and 'netbox-version' in json.loads(body or '{}'), status))
status, _ = get('/api/ipam/prefixes/', Authorization=f'Bearer {token}', Accept='application/json')
checks.append(('service token may read prefixes', status == 200, status))
status, _ = get('/api/users/users/', Authorization=f'Bearer {token}', Accept='application/json')
checks.append(('service token may not read users', status == 403, status))

for name, ok, code in checks:
    print(f"{'ok  ' if ok else 'FAIL'} {name} (HTTP {code})")
sys.exit(0 if all(ok for _, ok, _ in checks) else 1)
PY
echo "Lanvex Core image $image works."
