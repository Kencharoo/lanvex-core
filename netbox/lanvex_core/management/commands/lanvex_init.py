import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import ObjectType
from lanvex_core.service_account import ROLE_GROUPS, SERVICE_PERMISSIONS, TOKEN_PATTERN
from netbox.plugins import get_plugin_config
from users.models import Group, ObjectPermission, Token, User


class Command(BaseCommand):
    help = (
        "Set up what Lanvex needs in Lanvex Core: its service account, that account's permissions and "
        "API token (from LANVEX_CORE_SERVICE_TOKEN), and the groups for Lanvex roles. Safe to run on "
        "every start: it converges on the same state and removes any other token of the service account."
    )

    def handle(self, *args, **options):
        raw = os.environ.get('LANVEX_CORE_SERVICE_TOKEN', '')
        match = TOKEN_PATTERN.match(raw)
        if not match:
            raise CommandError(
                'LANVEX_CORE_SERVICE_TOKEN must be set to nbt_<12 letters or digits>.<40 letters or digits>. '
                'The Lanvex installer generates it.'
            )
        key, secret = match['key'], match['secret']
        username = get_plugin_config('lanvex_core', 'service_username')

        with transaction.atomic():
            user, created = User.objects.get_or_create(username=username)
            user.first_name = 'Lanvex'
            user.last_name = '(service account)'
            user.is_active = True
            user.is_superuser = False
            user.set_unusable_password()
            user.save()

            for spec in SERVICE_PERMISSIONS:
                permission = ObjectPermission.objects.filter(name=spec.name).first() or ObjectPermission(name=spec.name)
                permission.description = spec.description
                permission.enabled = True
                permission.actions = list(spec.actions)
                permission.constraints = None
                permission.save()
                permission.object_types.set([
                    ObjectType.objects.get_by_natural_key(*label.split('.')) for label in spec.object_types
                ])
                permission.users.set([user])
                permission.groups.clear()

            for name in ROLE_GROUPS:
                Group.objects.get_or_create(name=name)

            token = Token.objects.filter(key=key).first()
            if token is not None and not (token.user_id == user.pk and token.validate(secret)):
                token.delete()
                token = None
            if token is None:
                token = Token(user=user, version=2, key=key, token=secret, description='Used by Lanvex')
            token.enabled = True
            token.write_enabled = True
            token.expires = None
            token.full_clean(exclude=['user'])
            token.save()
            stale, _ = Token.objects.filter(user=user).exclude(pk=token.pk).delete()

        self.stdout.write(
            f"Lanvex service account '{username}' {'created' if created else 'up to date'}; "
            f"{len(SERVICE_PERMISSIONS)} permissions; API token {key} ready"
            + (f"; removed {stale} old token(s)" if stale else '')
            + '.'
        )
