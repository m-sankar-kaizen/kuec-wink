# -*- coding: utf-8 -*-
{
    'name': "WINK Portal Foundation",
    'summary': """
        Foundational module for KUEC WINK Shared Services Portal.
    """,
    'description': """
        Provides baseline security, branding, and core setup for the WINK Portal.
        This module establishes the core structural dependencies for all subsequent
        catalog, portal, and service delivery features.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenprinciples.com",
    'category': 'Hidden',
    'version': '18.0.1.0.0',
    'depends': [
        'base_setup',
        'portal', 
        'sale_management', 
        'sale_subscription', 
        'project', 
        'account', 
        'helpdesk', 
        'website', 
        'website_sale', 
        'web',
        'sign',
        'mass_mailing',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'views/portal_templates/branded_layout.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'kuec_portal_foundation/static/src/scss/wink_theme.scss',
            'kuec_portal_foundation/static/src/scss/wink_portal_lovable.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
