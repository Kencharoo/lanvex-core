#!/usr/bin/env bash
# Tests for Lanvex Core. Needs PostgreSQL and Redis on localhost, like NetBox's own test suite.
#
#   lanvex/scripts/test.sh          lint, fork check, Lanvex Core's tests
#   lanvex/scripts/test.sh --full   ... and NetBox's complete test suite (takes a long time)
#
# Database credentials: LANVEX_CORE_TEST_DB_NAME / _USER / _PASSWORD / _HOST (default netbox/netbox/netbox).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PY=${PYTHON:-python3}

"${RUFF:-ruff}" check netbox/lanvex_core netbox/lanvex_configuration.py netbox/lanvex_configuration_testing.py
lanvex/scripts/check-fork.sh
cd netbox
NETBOX_CONFIGURATION=lanvex_configuration_testing "$PY" manage.py test lanvex_core --keepdb
if [ "${1:-}" = "--full" ]; then
  NETBOX_CONFIGURATION=netbox.configuration_testing "$PY" manage.py test --keepdb --parallel "$(nproc)"
fi
