import importlib.util
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

HEALTHCHECK = Path(__file__).resolve().parents[3] / 'lanvex' / 'healthcheck.py'


def load():
    spec = importlib.util.spec_from_file_location('lanvex_healthcheck', HEALTHCHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RoleTest(SimpleTestCase):
    """The container health check must know the role from the first second, not only once it serves."""

    def role(self, *args):
        with tempfile.NamedTemporaryFile() as f:
            f.write(b'\0'.join(a.encode() for a in args) + b'\0')
            f.flush()
            return load().running_role(f.name)

    def test_roles_while_the_entrypoint_still_prepares(self):
        script = '/opt/lanvex-core/lanvex/docker-entrypoint.sh'
        self.assertEqual(self.role('/bin/sh', script, 'core'), 'core')
        self.assertEqual(self.role('/bin/sh', script), 'core')
        self.assertEqual(self.role('/bin/sh', script, 'worker'), 'worker')
        self.assertEqual(self.role('/bin/sh', script, 'manage', 'nbshell'), 'other')

    def test_roles_once_running(self):
        self.assertEqual(self.role('/opt/venv/bin/python', '/opt/venv/bin/gunicorn', '--bind', '0.0.0.0:8080'), 'core')
        self.assertEqual(self.role('python', 'manage.py', 'rqworker'), 'worker')
        self.assertEqual(self.role('python', 'manage.py', 'nbshell'), 'other')
