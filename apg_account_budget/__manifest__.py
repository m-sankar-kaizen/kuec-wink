# -*- coding: utf-8 -*-
{
    'name': 'Accounting Budget Management',
    'version': '18.0.0.0',
    'category': 'Accounting',
    'summary': """ Accounting Budget Management for Odoo 18. """,
    'description': """ Easily plan, monitor, and control your organization’s budgets with the
     Accounting Budget Management module. This tool streamlines financial planning, enhances cost control,
      and ensures budget compliance for improved decision-making.""",
    'author': 'Apagen Solutions Pvt Ltd',
    'company': 'Apagen Solutions Pvt Ltd',
    'maintainer': 'Apagen Solutions Pvt Ltd',
    'website': "https://www.apagen.com",
    'depends': ['base', 'account'],
    'data': [
        'security/account_budget_security.xml',
        'security/ir.model.access.csv',
        'views/account_analytic_account_views.xml',
        'views/account_budget_views.xml',
    ],
    'post_init_hook': 'enable_analytic_accounting',
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
