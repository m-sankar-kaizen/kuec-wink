# -*- coding: utf-8 -*-
{
    'name': "Notification Base",
    'summary': """
        Centralized Notification Email Configuration for System Messages and Alerts
    """,
    'description': """
        This module provides a base infrastructure for configuring system-level
        notification email addresses within Odoo. It introduces a customizable
        field in the system settings (under the Purchase tab) that allows the
        user to define a dedicated SRN (System Resource Notification) email address
        for the company.

        Key Features:
        - Adds a configurable SRN notification email field at the company level
        - Provides a related editable field in system settings (res.config.settings)
        - Can be used across modules to fetch a centralized email for sending
          automated purchase alerts, procurement status updates, or exception notices
        - Easily extendable by other modules that require standardized notification handling

        Designed for modular reuse by other notification-based modules in the Kaizen suite.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Administration/Technical Settings',
    'version': '1.2',
    'depends': ['base_setup', 'mail'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'auto_install': False,
}
