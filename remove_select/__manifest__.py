# -*- coding: utf-8 -*-
{
    'name': "Remove Database Selector",
    'summary': """
        Hides the database selector and 'Manage Databases' option from the Odoo login screen for better security.
    """,
    'description': """
        This module customizes the Odoo web login interface by:
        - Removing the 'Manage Databases' link on the login page.
        - Hiding the database dropdown typically shown when multiple databases exist.

        Use Cases:
        - Production environments where only a single database is used.
        - Scenarios where database visibility should be hidden from users for security, branding, or usability reasons.
        - Preventing access to the database manager through the web interface.

        This module is frontend-only and does not affect backend functionality or access control mechanisms.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Technical Settings',
    'version': '1.0',
    'depends': ['web'],
    'data': [
        'views/web_login_templates.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'auto_install': False,
}
