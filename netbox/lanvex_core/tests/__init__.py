from unittest import SkipTest

from django.conf import settings

# NetBox's own suite (lanvex/scripts/test.sh --full) runs with NetBox's test configuration, which does
# not load Lanvex Core; these tests need lanvex_configuration_testing and skip themselves otherwise.
if 'lanvex_core' not in settings.PLUGINS:
    raise SkipTest('Lanvex Core tests run with NETBOX_CONFIGURATION=lanvex_configuration_testing.')
