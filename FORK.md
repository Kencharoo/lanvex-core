# Lanvex Core

Lanvex Core is the network inventory and IPAM application behind Lanvex, built
on [NetBox](https://github.com/netbox-community/netbox) by NetBox Labs and the NetBox community. It is
NetBox with Lanvex's name, colours and typeface, single sign-on from Lanvex, and the setup Lanvex
needs. It is not NetBox and is not supported by NetBox Labs.

Base: the NetBox release in [`lanvex/UPSTREAM`](lanvex/UPSTREAM). NetBox's own documentation in
`docs/` applies unchanged; this file covers only what differs.

## How the fork is kept cheap to maintain

NetBox ships a patch release every two weeks and a feature release every four months. Every change
this fork makes to NetBox's own files can conflict with each of them, so:

1. **Lanvex's behaviour lives in its own package**, `netbox/lanvex_core/`, loaded through NetBox's
   plugin mechanism: single sign-on rules, theme, top-bar link, service account setup.
2. **Configuration lives in its own module**, `netbox/lanvex_configuration.py`, selected with
   `NETBOX_CONFIGURATION`. NetBox's settings files are untouched.
3. **NetBox's files are changed only where nothing else works**, each change is listed below with its
   reason, and each changed file carries a "Modified for Lanvex Core" notice (Apache License 2.0,
   section 4b). `lanvex/scripts/check-fork.sh` fails when either is missing.
4. **No database migrations of our own.** Lanvex Core adds no models, so NetBox's migrations never
   collide with ours.

## Changes to NetBox's files

| File | Change | Why it cannot live in lanvex_core |
|---|---|---|
| `netbox/templates/base/base.html` | Page title says "Lanvex Core" | The title is not a template block or extension point |
| `netbox/templates/base/layout.html` | Lanvex Core logo in the sidebar; "Lanvex Core, based on NetBox x.y.z" instead of the NetBox release name | Logo and release line are hard-coded; project templates take precedence over app templates |
| `netbox/templates/login.html` | Lanvex Core logo | Same |
| `README.md` | Short notice at the top that this is Lanvex Core, a fork | A fork must not present itself as NetBox |
| `NOTICE` | Attribution for Lanvex Core's additions | Apache License 2.0, section 4d |

## Files added outside lanvex/ and netbox/lanvex_core/

| File | Purpose |
|---|---|
| `FORK.md` | This file |
| `.dockerignore` | Build context for `lanvex/Dockerfile` |
| `netbox/lanvex_configuration.py` | Production configuration from environment variables |
| `netbox/lanvex_configuration_testing.py` | Test configuration: NetBox's plus lanvex_core and single sign-on |

## Single sign-on

Lanvex forwards `/core/` to Lanvex Core and adds `X-Lanvex-User`, `X-Lanvex-Display-Name`,
`X-Lanvex-Groups` (`lanvex-admin` or `lanvex-readonly`) and `X-Lanvex-Proxy-Secret`. NetBox's remote
authentication signs the user in; `lanvex_core.auth.LanvexRemoteUserBackend` accepts only requests
with the right proxy secret and never the service account. `lanvex_core.middleware` refuses browser
sessions used without the proxy and signs a user in again when their Lanvex role changed.
Administrators become superusers; every signed-in user may view everything (`EXEMPT_VIEW_PERMISSIONS`).

Lanvex itself uses the API as `lanvex-service`, with exactly the permissions in
`lanvex_core/service_account.py`. `manage.py lanvex_init` (run on every start of the container)
creates that account and its token from `LANVEX_CORE_SERVICE_TOKEN`.

## Merging a NetBox release

```bash
git remote add upstream https://github.com/netbox-community/netbox.git   # once
lanvex/scripts/merge-upstream.sh v4.7.6
lanvex/scripts/test.sh            # lint, fork check, Lanvex Core tests
lanvex/scripts/test.sh --full     # before a feature release (4.8.0 etc.): NetBox's whole suite too
docker build -f lanvex/Dockerfile -t lanvex-core .
```

The script refuses pre-releases and going backwards, stops on conflicts and lists them, and records
the new base in `lanvex/UPSTREAM`. Merge security releases within days.

## Building and running

The image runs as `core` (web application on port 8080, prepares the database on start), `worker`
(background jobs) or `manage <command>`. Lanvex's `docker-compose.yml` runs both roles, a PostgreSQL
and a Redis for Lanvex Core, and the Lanvex installer writes all settings. Lanvex Core publishes no
port: it is reachable only through Lanvex.

## Licence

NetBox is licensed under the Apache License 2.0 (`LICENSE.txt`, `NOTICE`); so are Lanvex Core's
additions. "NetBox" is a trademark of NetBox Labs; Lanvex Core uses the name only to say what it is
based on. IBM Plex fonts in `netbox/lanvex_core/static/lanvex_core/fonts/` are under the SIL Open Font
License 1.1.
