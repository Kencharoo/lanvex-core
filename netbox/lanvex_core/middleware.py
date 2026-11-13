import logging

from django.conf import settings
from django.contrib import auth
from django.http import HttpResponseForbidden

from .auth import proxy_verified

__all__ = ('LanvexProxyMiddleware',)

GROUPS_SESSION_KEY = 'lanvex_core_groups'

logger = logging.getLogger('lanvex_core.middleware')


class LanvexProxyMiddleware:
    """
    Two rules for browser sessions, enforced after NetBox's RemoteUserMiddleware has run:

    1. A signed-in session is only usable through the Lanvex proxy. A session cookie replayed
       against Lanvex Core directly is logged out and refused.
    2. A session follows the user's current Lanvex role. NetBox syncs groups (and with them
       superuser status) only when it signs a user in, so when the groups Lanvex sends differ from
       those the session started with, the user is signed in again with the new ones.

    API requests authenticated with a token do not carry a session user at this point and are left
    to NetBox's token authentication.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            if not proxy_verified(request):
                logger.warning('Refused a session for %s that did not come through the Lanvex proxy.', user)
                auth.logout(request)
                return _refused()
            groups = request.META.get(settings.REMOTE_AUTH_GROUP_HEADER, '')
            started_with = request.session.get(GROUPS_SESSION_KEY)
            if started_with is None:
                request.session[GROUPS_SESSION_KEY] = groups
            elif started_with != groups:
                user = self._sign_in_again(request, groups)
                if user is None:
                    return _refused()
        return self.get_response(request)

    @staticmethod
    def _sign_in_again(request, groups):
        username = request.META.get(settings.REMOTE_AUTH_HEADER)
        auth.logout(request)
        if not username:
            return None
        separator = settings.REMOTE_AUTH_GROUP_SEPARATOR
        user = auth.authenticate(
            request, remote_user=username, remote_groups=[g for g in groups.split(separator) if g]
        )
        if user is None:
            return None
        auth.login(request, user)
        request.user = user
        request.session[GROUPS_SESSION_KEY] = groups
        logger.info('Signed %s in again: their Lanvex role changed.', user)
        return user


def _refused():
    return HttpResponseForbidden(
        'Lanvex Core can only be used through Lanvex. Open it from Lanvex.\n', content_type='text/plain; charset=utf-8'
    )
