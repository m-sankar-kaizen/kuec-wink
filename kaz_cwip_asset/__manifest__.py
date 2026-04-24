# -*- coding: utf-8 -*-
{
    'name': 'Transfer CWIP to Fixed Asset',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Transfer CWIP to Fixed Asset',
    'description': """Transfer CWIP to Fixed Asset""",
    'author': 'Kaizen Principles',
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': ['account_asset',
                ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/res_settings_views.xml',
        'wizards/cwip_wizard_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

