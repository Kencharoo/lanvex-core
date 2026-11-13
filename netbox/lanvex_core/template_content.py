from netbox.plugins import PluginTemplateExtension, get_plugin_config

from .version import __version__


class LanvexChrome(PluginTemplateExtension):
    """Lanvex's colours, typeface and favicon on every page, and the way back to Lanvex in the top bar."""

    def head(self):
        return self.render('lanvex_core/head.html', {'lanvex_core_version': __version__})

    def navbar(self):
        return self.render('lanvex_core/navbar.html', {'lanvex_url': get_plugin_config('lanvex_core', 'lanvex_url')})


template_extensions = [LanvexChrome]
