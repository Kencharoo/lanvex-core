"""
Single sign-on from Lanvex.

Lanvex Core runs behind Lanvex, which forwards requests under /core/ and tells Lanvex Core who the
signed-in Lanvex user is (NetBox's remote authentication: REMOTE_AUTH_HEADER and friends, set in
lanvex_configuration.py). A header is only as trustworthy as whoever can send it, so every request
that signs a user in must also carry the proxy secret shared with Lanvex. Lanvex Core is not
published outside the Docker network either; the secret is the second lock.
"""
import hmac
import logging

from netbox.authentication import RemoteUserBackend
from netbox.plugins import get_plugin_config

__all__ = ('PROXY_SECRET_HEADER', 'LanvexRemoteUserBackend', 'proxy_verified')

PROXY_SECRET_HEADER = 'HTTP_X_LANVEX_PROXY_SECRET'
MIN_SECRET_LENGTH = 32

logger = logging.getLogger('lanvex_core.auth')


def proxy_verified(request):
    """True if the request carries the proxy secret. A missing or short configured secret trusts nothing."""
    secret = get_plugin_config('lanvex_core', 'proxy_secret') or ''
    if len(secret) < MIN_SECRET_LENGTH:
        return False
    given = request.META.get(PROXY_SECRET_HEADER, '')
    return hmac.compare_digest(given.encode(), secret.encode())


class LanvexRemoteUserBackend(RemoteUserBackend):
    """NetBox's remote-user backend, accepting only users vouched for by the Lanvex proxy."""

    def authenticate(self, request, remote_user, remote_groups=None):
        if request is None or not proxy_verified(request):
            logger.warning('Refused sign-in as %r: the request did not come through the Lanvex proxy.', remote_user)
            return None
        if remote_user == get_plugin_config('lanvex_core', 'service_username'):
            logger.warning('Refused sign-in as %r: reserved for Lanvex itself.', remote_user)
            return None
        return super().authenticate(request, remote_user, remote_groups)
