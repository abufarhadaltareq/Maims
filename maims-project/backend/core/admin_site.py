"""Custom admin site for Maims.

The home page is a responsive store dashboard for daily order work, stock alerts,
and common catalogue and settings tasks.

The site subclasses :class:`unfold.sites.UnfoldAdminSite` so every page is served
with Unfold's Tailwind shell. The numbers on the home page are supplied by
``core.admin.dashboard_callback`` (wired up through ``UNFOLD`` in settings), which
is also what Unfold's dashboard template reads.
"""
from unfold.sites import UnfoldAdminSite


class MaimsAdminSite(UnfoldAdminSite):
    site_header = 'Maims Store Admin'
    site_title = 'Maims Admin'
    index_title = 'Maims Store'
    enable_nav_sidebar = True

    # No `class Media` here on purpose: the Maims stylesheet is injected once for
    # every admin page through UNFOLD["STYLES"] (see core/settings.py), so declaring
    # it here as well would load it twice.


maims_admin = MaimsAdminSite(name='admin')
