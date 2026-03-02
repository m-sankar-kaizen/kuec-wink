# -*- coding: utf-8 -*-
"""UI tests for KUEC Service Catalogue (WINK Portal)."""
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestWinkUITour(HttpCase):
    """Run WINK portal tours via headless browser (requires Chrome + websocket-client)."""

    def test_wink_guest_tour_services(self):
        """Run wink_guest_tour on /services (public catalogue page)."""
        self.start_tour('/services', 'wink_guest_tour', login=None)


@tagged('post_install', '-at_install')
class TestWinkPages(HttpCase):
    """HTTP tests for WINK portal pages (no browser required)."""

    def test_services_page_loads(self):
        """Verify /services catalogue page loads and returns 200."""
        response = self.url_open('/services')
        self.assertEqual(response.status_code, 200, '/services should return 200')
        # Ensure WINK catalogue content is present
        html = response.text
        self.assertIn('wink-catalogue-header', html, 'Page should contain WINK catalogue header')
