from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import User

SECRET = settings.PLUGINS_CONFIG['lanvex_core']['proxy_secret']


def via_lanvex(username, groups='lanvex-admin', secret=SECRET, display_name=None):
    headers = {'HTTP_X_LANVEX_USER': username, 'HTTP_X_LANVEX_GROUPS': groups}
    if secret is not None:
        headers['HTTP_X_LANVEX_PROXY_SECRET'] = secret
    if display_name:
        headers['HTTP_X_LANVEX_DISPLAY_NAME'] = display_name
    return headers


class SignInTest(TestCase):
    """Users are signed in only when Lanvex vouches for them with the shared proxy secret."""

    def test_header_without_secret_does_not_sign_in(self):
        response = self.client.get(reverse('home'), **via_lanvex('mallory', secret=None))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        self.assertFalse(User.objects.filter(username='mallory').exists())

    def test_wrong_secret_does_not_sign_in(self):
        response = self.client.get(reverse('home'), **via_lanvex('mallory', secret=SECRET[:-1] + '!'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='mallory').exists())

    @override_settings(PLUGINS_CONFIG={'lanvex_core': {'proxy_secret': 'short'}})
    def test_a_short_configured_secret_trusts_nobody(self):
        response = self.client.get(reverse('home'), **via_lanvex('mallory', secret='short'))
        self.assertEqual(response.status_code, 302)

    def test_nobody_can_sign_in_as_the_service_account(self):
        response = self.client.get(reverse('home'), **via_lanvex('lanvex-service'))
        self.assertEqual(response.status_code, 302)

    def test_failed_sign_in_from_lanvex_is_explained_instead_of_an_empty_login_page(self):
        response = self.client.get(reverse('home'), follow=True, **via_lanvex('mallory', secret='x' * 40))
        self.assertEqual(response.status_code, 403)
        self.assertIn('could not sign you in', response.content.decode())
        response = self.client.get(reverse('login'), **via_lanvex('lanvex-service'))
        self.assertEqual(response.status_code, 403)
        # Without Lanvex's headers (the container health check) the login page answers as usual.
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)

    def test_lanvex_admin_becomes_superuser_with_display_name(self):
        response = self.client.get(reverse('home'), **via_lanvex('marco', display_name='Marco'))
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='marco')
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.first_name, 'Marco')
        self.assertEqual([g.name for g in user.groups.all()], ['lanvex-admin'])

    def test_read_only_user_can_view_but_not_change(self):
        headers = via_lanvex('reader', groups='lanvex-readonly')
        self.assertEqual(self.client.get(reverse('ipam:prefix_list'), **headers).status_code, 200)
        self.assertEqual(self.client.get(reverse('ipam:prefix_add'), **headers).status_code, 403)
        self.assertEqual(self.client.get(reverse('users:user_list'), **headers).status_code, 403)
        self.assertFalse(User.objects.get(username='reader').is_superuser)


class SessionTest(TestCase):
    """A browser session is bound to the proxy and to the user's current Lanvex role."""

    def test_role_change_applies_to_an_existing_session(self):
        self.assertEqual(self.client.get(reverse('ipam:prefix_add'), **via_lanvex('marco')).status_code, 200)
        downgraded = via_lanvex('marco', groups='lanvex-readonly')
        self.assertEqual(self.client.get(reverse('ipam:prefix_add'), **downgraded).status_code, 403)
        self.assertFalse(User.objects.get(username='marco').is_superuser)
        self.assertEqual(self.client.get(reverse('ipam:prefix_add'), **via_lanvex('marco')).status_code, 200)

    def test_session_used_without_the_proxy_is_refused_and_ended(self):
        self.assertEqual(self.client.get(reverse('home'), **via_lanvex('marco')).status_code, 200)
        response = self.client.get(reverse('ipam:prefix_list'))
        self.assertEqual(response.status_code, 403)
        self.assertIn('only be used through Lanvex', response.content.decode())
        # The session is gone: without headers the user is anonymous again.
        self.assertEqual(self.client.get(reverse('ipam:prefix_list')).status_code, 302)

    def test_switching_lanvex_user_switches_the_session_user(self):
        self.client.get(reverse('home'), **via_lanvex('marco'))
        response = self.client.get(reverse('home'), **via_lanvex('anna', groups='lanvex-readonly'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.user.username, 'anna')
        self.assertFalse(response.wsgi_request.user.is_superuser)


class BrandingTest(TestCase):

    def test_pages_carry_lanvex_core_branding_and_a_way_back(self):
        html = self.client.get(reverse('home'), **via_lanvex('marco')).content.decode()
        self.assertIn('<title>Home | Lanvex Core</title>', html)
        self.assertIn('lanvex_core/lanvex-core-logo-light.svg', html)
        self.assertIn('lanvex_core/lanvex-core.css', html)
        self.assertIn('Back to Lanvex', html)
        self.assertIn('Based on NetBox', html)
        self.assertNotIn('netboxlabs.com/netbox-cloud', html)


class ScriptingTest(TestCase):
    """Scripts use the API with a Lanvex session: any API response gives them the CSRF cookie for writes."""

    def test_api_responses_set_the_csrf_cookie(self):
        client = self.client_class(enforce_csrf_checks=True)
        headers = via_lanvex('marco')
        response = client.get('/' + settings.BASE_PATH + 'api/status/', **headers)
        self.assertEqual(response.status_code, 200)
        token = response.cookies[settings.CSRF_COOKIE_NAME].value
        site = {'name': 'Lab', 'slug': 'lab'}
        url = '/' + settings.BASE_PATH + 'api/dcim/sites/'
        refused = client.post(url, site, content_type='application/json', **headers)
        self.assertEqual(refused.status_code, 403)  # without the token
        created = client.post(url, site, content_type='application/json', HTTP_X_CSRFTOKEN=token, **headers)
        self.assertEqual(created.status_code, 201, created.content)
