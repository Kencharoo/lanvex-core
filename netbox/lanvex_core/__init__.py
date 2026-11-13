"""
Lanvex Core: everything in this NetBox fork that is Lanvex's own.

Lanvex Core is NetBox with Lanvex's branding and single sign-on. To keep upstream merges cheap, the
fork's own behaviour lives in this package, loaded through NetBox's plugin mechanism, instead of in
edits to NetBox's code. FORK.md at the repository root lists every file outside this package that
the fork changes.
"""
from netbox.plugins import PluginConfig

from .version import __version__


class LanvexCoreConfig(PluginConfig):
    name = 'lanvex_core'
    verbose_name = 'Lanvex Core'
    description = 'Single sign-on through Lanvex, branding, and the Lanvex service account'
    version = __version__
    author = 'Lanvex'
    base_url = 'lanvex'
    min_version = '4.7.0'
    # Runs after NetBox's RemoteUserMiddleware: see middleware.py.
    middleware = ['lanvex_core.middleware.LanvexProxyMiddleware']
    default_settings = {
        # Shared with Lanvex. Only requests carrying it may sign a user in or use a browser session.
        'proxy_secret': '',
        # Where "Back to Lanvex" leads; relative to the site when Lanvex Core is served under /core/.
        'lanvex_url': '/',
        # The account Lanvex itself uses through the API. Nobody can sign in as it through the proxy.
        'service_username': 'lanvex-service',
    }


config = LanvexCoreConfig
