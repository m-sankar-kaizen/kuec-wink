# -*- coding: utf-8 -*-
{
    'name': 'SSO Login Extension',
    'summary': 'Custom Single Sign-On (SSO) integration '
               'using SAML and OAuth for Ankabut login portal.',
    'description': """
        Kaizen SSO Solution for Ankabut (KUEC)

        This module provides a customizable and secure Single Sign-On (SSO) experience
        for the Ankabut login portal. It integrates with both SAML and OAuth providers,
        including Microsoft Azure Active Directory, allowing institutions to seamlessly
        authenticate users via federated identity providers.

        Key Features:
        - Hide or show the default Odoo login form conditionally
        - Custom branding with organization logos
        - SAML/OAuth provider logos shown on login page
        - Frontend layout enhancements
        - Web login controller extension
        - Configuration options in General Settings

        Suitable for:
        - Government/university portals
        - Institutions using Azure, Ankabut Federation, or custom IdPs
    """,
    'author': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'category': 'Authentication',
    'version': '1.0',
    'depends': ['auth_saml',
                'microsoft_azure_sso_integration',
                'web_enterprise',
                'website'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/auth_oauth_provider_views.xml',
        'views/auth_saml_provider_views.xml',
        'views/webclient_templates.xml',
        'views/website_templates.xml',
    ],
    'assets': {

        # 'web.assets_frontend': [
        #     'kaz_login_kuec_ank/static/src/scss/style.scss',
        # ],

    },
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'auto_install': False,
}
