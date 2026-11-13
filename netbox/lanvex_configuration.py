"""
Lanvex Core configuration, read from the environment.

Selected with NETBOX_CONFIGURATION=lanvex_configuration (the container image sets it). The Lanvex
installer writes every value into Lanvex's .env; nothing here is a secret.

Lanvex Core is reachable only through Lanvex, which forwards /core/ to it and signs users in with
the headers configured below. See lanvex_core/auth.py.
"""
import os


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f'{name} must be set. The Lanvex installer writes it into .env.')
    return value


def env_bool(name, default=False):
    return env(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


# Only Lanvex reaches Lanvex Core (it is not published outside the Docker network), and Lanvex passes
# on the host name the browser used, so any host name is acceptable here.
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('LANVEX_CORE_DB_NAME', 'lanvex_core'),
        'USER': env('LANVEX_CORE_DB_USER', 'lanvex_core'),
        'PASSWORD': env('LANVEX_CORE_DB_PASSWORD', required=True),
        'HOST': env('LANVEX_CORE_DB_HOST', 'core-db'),
        'PORT': env('LANVEX_CORE_DB_PORT', ''),
        'CONN_MAX_AGE': 300,
    }
}

_redis = {
    'HOST': env('LANVEX_CORE_REDIS_HOST', 'core-redis'),
    'PORT': int(env('LANVEX_CORE_REDIS_PORT', '6379')),
    'USERNAME': '',
    'PASSWORD': env('LANVEX_CORE_REDIS_PASSWORD', ''),
    'SSL': False,
}
REDIS = {
    'tasks': {**_redis, 'DATABASE': int(env('LANVEX_CORE_REDIS_TASKS_DB', '0'))},
    'caching': {**_redis, 'DATABASE': int(env('LANVEX_CORE_REDIS_CACHE_DB', '1'))},
}

SECRET_KEY = env('LANVEX_CORE_SECRET_KEY', required=True)
API_TOKEN_PEPPERS = {1: env('LANVEX_CORE_API_TOKEN_PEPPER', required=True)}

# Served by Lanvex under /core/.
BASE_PATH = env('LANVEX_CORE_BASE_PATH', 'core/')
SESSION_COOKIE_NAME = 'lanvex_core_session'
CSRF_COOKIE_NAME = 'lanvex_core_csrftoken'
LOGIN_TIMEOUT = 12 * 3600  # A Lanvex Core session never outlives Lanvex's own maximum session.
TIME_ZONE = env('LANVEX_CORE_TIME_ZONE', 'UTC')
DEBUG = env_bool('LANVEX_CORE_DEBUG')
if env('LANVEX_CORE_MEDIA_ROOT'):
    MEDIA_ROOT = env('LANVEX_CORE_MEDIA_ROOT')

# Single sign-on from Lanvex: Lanvex sends the signed-in user, their display name and their role as
# a group, together with the shared proxy secret that lanvex_core.auth checks before trusting them.
REMOTE_AUTH_ENABLED = True
REMOTE_AUTH_BACKEND = 'lanvex_core.auth.LanvexRemoteUserBackend'
REMOTE_AUTH_HEADER = 'HTTP_X_LANVEX_USER'
REMOTE_AUTH_USER_FIRST_NAME = 'HTTP_X_LANVEX_DISPLAY_NAME'
REMOTE_AUTH_USER_LAST_NAME = 'HTTP_X_LANVEX_UNUSED_LAST_NAME'
REMOTE_AUTH_USER_EMAIL = 'HTTP_X_LANVEX_UNUSED_EMAIL'
REMOTE_AUTH_AUTO_CREATE_USER = True
REMOTE_AUTH_GROUP_SYNC_ENABLED = True
REMOTE_AUTH_AUTO_CREATE_GROUPS = True
REMOTE_AUTH_GROUP_HEADER = 'HTTP_X_LANVEX_GROUPS'
REMOTE_AUTH_GROUP_SEPARATOR = ','
REMOTE_AUTH_SUPERUSER_GROUPS = ['lanvex-admin']
REMOTE_AUTH_DEFAULT_GROUPS = []
REMOTE_AUTH_DEFAULT_PERMISSIONS = {}

# Every signed-in Lanvex user may look at everything; only Lanvex administrators (superusers here)
# may change anything. Signing in happens in Lanvex, never on Lanvex Core's own login page.
LOGIN_REQUIRED = True
EXEMPT_VIEW_PERMISSIONS = ['*']
LOGIN_FORM_HIDDEN = True

# No links to NetBox Labs' commercial offers, no outbound census or release checks.
ISOLATED_DEPLOYMENT = True
CENSUS_REPORTING_ENABLED = False
RELEASE_CHECK_URL = None

PLUGINS = ['lanvex_core']
PLUGINS_CONFIG = {
    'lanvex_core': {
        'proxy_secret': env('LANVEX_CORE_PROXY_SECRET', required=True),
        'lanvex_url': env('LANVEX_CORE_LANVEX_URL', '/'),
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'plain': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'}},
    'root': {'handlers': ['console'], 'level': env('LANVEX_CORE_LOG_LEVEL', 'INFO')},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
