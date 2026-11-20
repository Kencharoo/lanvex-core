import os
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from extras.models import CustomField
from lanvex_core.service_account import CUSTOM_FIELDS, SERVICE_PERMISSIONS
from users.models import Group, ObjectPermission, Token, User

TOKEN = 'nbt_AbCdEf123456.' + 'Q' * 20 + 'r' * 20
OTHER = 'nbt_ZyXwVu654321.' + 'S' * 40


def run(token=TOKEN):
    out = StringIO()
    with mock.patch.dict(os.environ, {'LANVEX_CORE_SERVICE_TOKEN': token}):
        call_command('lanvex_init', stdout=out)
    return out.getvalue()


def api(token=TOKEN):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


class LanvexInitTest(TestCase):

    def test_creates_the_service_account_with_exactly_the_documented_permissions(self):
        self.assertIn("'lanvex-service' created", run())
        user = User.objects.get(username='lanvex-service')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.has_usable_password())
        granted = {
            p.name: (sorted(p.actions), sorted(f'{t.app_label}.{t.model}' for t in p.object_types.all()))
            for p in ObjectPermission.objects.filter(users=user)
        }
        self.assertEqual(granted, {
            s.name: (sorted(s.actions), sorted(s.object_types)) for s in SERVICE_PERMISSIONS
        })
        self.assertTrue(Group.objects.filter(name='lanvex-admin').exists())
        self.assertTrue(Group.objects.filter(name='lanvex-readonly').exists())

    def test_the_token_works_and_is_limited(self):
        run()
        self.assertEqual(api().get(reverse('ipam-api:prefix-list')).status_code, 200)
        self.assertEqual(api().post(reverse('ipam-api:prefix-list'), {'prefix': '10.1.0.0/24'}).status_code, 201)
        self.assertEqual(api().post(reverse('dcim-api:site-list'), {'name': 'x', 'slug': 'x'}).status_code, 403)
        self.assertEqual(api(OTHER).get(reverse('ipam-api:prefix-list')).status_code, 403)

    def test_running_again_changes_nothing(self):
        run()
        before = list(Token.objects.values_list('pk', 'hmac_digest'))
        self.assertIn('up to date', run())
        self.assertEqual(list(Token.objects.values_list('pk', 'hmac_digest')), before)
        self.assertEqual(ObjectPermission.objects.count(), len(SERVICE_PERMISSIONS))

    def test_a_new_token_replaces_the_old_one(self):
        run()
        self.assertIn('removed 1 old token', run(OTHER))
        self.assertEqual(api(TOKEN).get(reverse('ipam-api:prefix-list')).status_code, 403)
        self.assertEqual(api(OTHER).get(reverse('ipam-api:prefix-list')).status_code, 200)

    def test_permissions_drift_is_repaired(self):
        run()
        permission = ObjectPermission.objects.get(name=SERVICE_PERMISSIONS[0].name)
        permission.actions = ['view', 'add', 'change', 'delete', 'run']
        permission.save()
        run()
        permission.refresh_from_db()
        self.assertEqual(sorted(permission.actions), sorted(SERVICE_PERMISSIONS[0].actions))

    def test_refuses_a_malformed_token(self):
        for bad in ('', 'nbt_short.x', TOKEN + 'x', '0123456789abcdef0123456789abcdef01234567'):
            with self.assertRaises(CommandError):
                run(bad)

    def test_creates_the_dhcp_custom_fields(self):
        run()
        for spec in CUSTOM_FIELDS:
            field = CustomField.objects.get(name=spec.name)
            self.assertEqual(field.type, spec.type)
            self.assertEqual([f'{t.app_label}.{t.model}' for t in field.object_types.all()], [spec.object_type])
        # The service account fills them in through the API, validated like any custom field.
        run()
        ip = {'address': '192.168.50.20/24', 'custom_fields': {'mac_address': 'aa:bb:cc:00:00:02'}}
        self.assertEqual(api().post(reverse('ipam-api:ipaddress-list'), ip, format='json').status_code, 201)
        bad = {'address': '192.168.50.21/24', 'custom_fields': {'mac_address': 'AA-BB'}}
        self.assertEqual(api().post(reverse('ipam-api:ipaddress-list'), bad, format='json').status_code, 400)
        pool = {
            'start_address': '192.168.50.100/24',
            'end_address': '192.168.50.199/24',
            'custom_fields': {'dhcp_lease_time': '2h'},
        }
        self.assertEqual(api().post(reverse('ipam-api:iprange-list'), pool, format='json').status_code, 201)
        self.assertEqual(CustomField.objects.filter(name__in=[s.name for s in CUSTOM_FIELDS]).count(), 3)
        self.assertEqual(CustomField.objects.get(name='lanvex_access').type, 'json')

    def test_records_settings_on_devices_but_does_not_add_or_delete_them(self):
        from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site

        run()
        site = Site.objects.create(name='School', slug='school')
        maker = Manufacturer.objects.create(name='Generic', slug='generic')
        kind = DeviceType.objects.create(manufacturer=maker, model='Server', slug='server')
        role = DeviceRole.objects.create(name='Server', slug='server')
        device = Device.objects.create(name='gw1', site=site, device_type=kind, role=role)
        url = reverse('dcim-api:device-detail', kwargs={'pk': device.pk})
        data = {'local_context_data': {'lanvex': {'dns_servers': ['10.0.0.53']}}}
        r = api().patch(url, data, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['config_context'], {'lanvex': {'dns_servers': ['10.0.0.53']}})
        self.assertEqual(api().delete(url).status_code, 403)
        new = {'name': 'gw2', 'site': site.pk, 'device_type': kind.pk, 'role': role.pk}
        self.assertEqual(api().post(reverse('dcim-api:device-list'), new, format='json').status_code, 403)
