# -*- coding: utf-8 -*-
{
    'name': 'Expense Funding',
    'version': '18.0.0.2',
    'sequence': 7,
    'category': 'Accounting',
    'summary': 'Petty cash and Credit Card transaction management',
    'depends': ['account_accountant', 'analytic', 'hr', 'hr_expense'],
    'data': [
            'security/ir.model.access.csv',
            'data/data.xml',
            'views/menuitem.xml',
            'views/account_journal.xml',
            'wizard/petty_cash_operation_view.xml',
            'views/petty_cash_request_view.xml',
            'views/credit_card_request.xml',
            'views/petty_cash_settelement_view.xml',
            'views/res_config_settings.xml'
        ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/logo.png'],
}
