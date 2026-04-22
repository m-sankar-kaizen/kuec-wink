# -*- coding: utf-8 -*-
{
    'name': 'PO Close Out',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'summary': 'PO Close Out Report',
    'description': """PO Close Out Report""",
    'author': 'Kaizen Principles',
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': ['purchase',
                'material_purchase_requisitions'],
    'data': [
        'views/res_config_settings_views.xml',
        'reports/purchase_incomplete_report.xml',
        'views/menu.xml'
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

