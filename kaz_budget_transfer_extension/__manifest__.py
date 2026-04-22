# -*- coding: utf-8 -*-
{
    'name': 'Budget Transfer Extension',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Budget Transfer Extension',
    'description': """Budget Transfer Extension""",
    'author': 'Kaizen Principles',
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': ['kz_requisition_quintuple_approvals',
                'analytic',
                'kaz_account_classification',
                'kaz_budget_line_progress'
                ],
    'data': [
        'views/budget_line_views.xml',
        'views/budget_transfer_wizard_views.xml',
        'views/material_purchase_requisition_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}