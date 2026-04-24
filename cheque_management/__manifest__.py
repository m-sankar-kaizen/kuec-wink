# -*- coding: utf-8 -*-
{
    'name': 'Cheque Management',
    'version': '18.0',
    'author': 'revalue',
    'category': 'Accounting',
    'description': """cheques management in odoo""",
    'website': '',
    'summary': """""",
    'depends': [
        'base',
        'mail',
        'account',
        'hr',
        'purchase',
        'sale',
        'hr_expense',
        'account_accountant'
    ],
    "license": "",
    "price": "",
    "currency": "",
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'security/security.xml',
        'views/account_payment.xml',
        'views/cheque_management.xml',
        'views/res_config.xml',
        'wizard/cheque_date_wizard_view.xml',
        'wizard/batch_monetization.xml',

    ],
    'images': ['static/description/icon.jpeg'],
    'installable': True,
    'auto_install': False,
}
