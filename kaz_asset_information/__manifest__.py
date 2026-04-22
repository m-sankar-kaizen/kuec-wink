# -*- coding: utf-8 -*-
{
    'name': "Asset Information",
    'summary': "Adds additional fields to asset records for better tracking and identification.",
    'description': """
This module extends the Account Asset functionality in Odoo by adding additional informational 
fields such as:
- Asset Number
- Tag Number
- Serial Number
- Site
- Room
It helps organizations maintain more detailed records for physical assets.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['account_asset'],
    'data': [
        'views/account_asset_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
