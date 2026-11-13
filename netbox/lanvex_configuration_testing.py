"""
Test configuration for Lanvex Core: NetBox's own test configuration plus the lanvex_core package and
the single sign-on settings of lanvex_configuration.py.

    NETBOX_CONFIGURATION=lanvex_configuration_testing python manage.py test lanvex_core

NetBox's own test suite still runs with NETBOX_CONFIGURATION=netbox.configuration_testing.
"""
import os

from netbox.configuration_testing import *  # noqa: F403

DATABASES['default'].update({  # noqa: F405
    'NAME': os.environ.get('LANVEX_CORE_TEST_DB_NAME', 'netbox'),
    'USER': os.environ.get('LANVEX_CORE_TEST_DB_USER', 'netbox'),
    'PASSWORD': os.environ.get('LANVEX_CORE_TEST_DB_PASSWORD', 'netbox'),
    'HOST': os.environ.get('LANVEX_CORE_TEST_DB_HOST', 'localhost'),
})

PROXY_SECRET_FOR_TESTS = 'test-proxy-secret-0123456789-0123456789-0123456789'

# Reuse the production single sign-on settings rather than restating them.
for _name in ('LANVEX_CORE_DB_PASSWORD', 'LANVEX_CORE_SECRET_KEY', 'LANVEX_CORE_API_TOKEN_PEPPER'):
    os.environ.setdefault(_name, 'only-imported-for-its-sign-on-settings-' + 'x' * 30)
os.environ.setdefault('LANVEX_CORE_PROXY_SECRET', PROXY_SECRET_FOR_TESTS)
import lanvex_configuration as _production  # noqa: E402

for _name in dir(_production):
    if _name.startswith('REMOTE_AUTH_') or _name in (
        'EXEMPT_VIEW_PERMISSIONS', 'LOGIN_FORM_HIDDEN', 'SESSION_COOKIE_NAME', 'CSRF_COOKIE_NAME',
        'ISOLATED_DEPLOYMENT',
    ):
        globals()[_name] = getattr(_production, _name)

PLUGINS = [*PLUGINS, 'lanvex_core']  # noqa: F405
PLUGINS_CONFIG = {'lanvex_core': {'proxy_secret': PROXY_SECRET_FOR_TESTS, 'lanvex_url': '/'}}
