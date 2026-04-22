# -*- coding: utf-8 -*-
{
    'name': 'Microsoft Azure OAuth2 SSO Integration',
    'version': "1.0",
    'summary': """Login to Odoo using Microsoft Azure accounts via OAuth2 Single Sign-On (SSO).""",
    'description': """
        This module enables Single Sign-On (SSO) functionality in Odoo using Microsoft Azure OAuth2 authentication.
        Users can log in to Odoo with their Microsoft accounts securely without entering credentials every time.
        It streamlines access for organizations using Azure Active Directory for identity management.
    """,
    'author': 'Kaizen Principles',
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': "https://www.kaizenae.com",
    'category': 'Extra Tools',
    'depends': ['auth_oauth'],
    'data': [
        'data/auth_oauth_provider_data.xml',
        'views/auth_oauth_provider_views.xml',
        'views/auth_oauth_templates.xml',
    ],
    'external_dependencies': {
        'python': ['pyjwt']
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
