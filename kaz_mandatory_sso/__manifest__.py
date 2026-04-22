# -*- coding: utf-8 -*-
{
    'name': 'Make SSO Mandatory',
    'summary': 'Enforces mandatory Single Sign-On (SSO) '
               'configuration for each user using SAML or OAuth.',
    'description': """
        Kaizen - Make SSO Mandatory for Users

        This module customizes the Odoo user form to enforce a Single Sign-On (SSO) method
        for each user. Administrators are required to select either a SAML or OAuth provider
        during user creation or update. This ensures that users are properly configured for
        external authentication and simplifies account management.

        Features:
        - Adds an `SSO Type` selection field (SAML or OAuth) to `res.users`
        - Requires assigning an appropriate identity provider based on the selected SSO type
        - Dynamically shows/hides the `saml_id` or `oauth_id` fields
        - Enforces configuration at the UI level for better security and clarity

        This module is particularly useful when integrating:
        - Microsoft Azure Active Directory (via OAuth)
        - Ankabut Federation or Shibboleth (via SAML)
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Extra Tools',
    'version': '1.0',
    'depends': ['microsoft_azure_sso_integration', 'auth_saml'],
    'data': [
        'views/res_users_views.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
