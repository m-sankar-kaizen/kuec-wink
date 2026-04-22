# -*- coding: utf-8 -*-
{
    'name': "Asset Manual Post Entries",
    'summary': "Allows manual posting of asset-related accounting entries.",
    'description': """
        This module enables users to manually control the posting of asset journal entries.
        It overrides default behavior to support posting conditions such as draft handling,
        asset validation bypass, or conditional posting via user input or wizard context.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Accounting/Assets',
    'version': '1.0',
    'depends': ['account_asset'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
