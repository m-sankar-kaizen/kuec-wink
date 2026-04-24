# -*- coding: utf-8 -*-
{
    'name': 'Related Party Balances',
    'version': '18.0.1.0.1',
    'category': 'Accounting',
    'summary': 'Related Party Balances',
    'description': """Related Party Balances""",
    'author': 'Kaizen Principles',
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': ['account',
                ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/related_party_entries_views.xml',
        'views/res_settings_views.xml',
        'views/account_account_views.xml',

    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
