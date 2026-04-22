# -*- coding: utf-8 -*-
{
    'name': 'Budget Line Progress',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Budget Line Progress',
    'description': """Budget Line Progress""",
    'author': 'Kaizen Principles',
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': ['kz_requisition_quintuple_approvals',
                'analytic',
                'kaz_account_classification',
                'kaz_company_restriction_base'
                ],
    'data': [
        'data/budget_line_seq.xml',
        'views/budget_analytic_views.xml',
        'views/budget_line_views.xml',
        'views/account_budget_post_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}