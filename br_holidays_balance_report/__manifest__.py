# -*- coding: utf-8 -*-
{
    'name': 'HR Balance Leave Report',
    'summary': 'Allocated balance, taken leaves and remaining balance per leave type for each employee',
    'description': 'User Can view Allocated balance, taken leaves and remaining balance per leave type for '
                   'each employee',
    'author': 'Tony Saji',
    'company': 'Tony Saji',
    'website': 'https://tony.com',
    'license': 'AGPL-3',
    'email': "tonyankabut@gmail.com",
    'version': '1.0',
    'category': 'Human Resources/Time Off',
    'depends': ['hr_holidays'],
    'data': [
        'security/balance_report_security.xml',
        'security/ir.model.access.csv',
        'report/leave_balance_report_view.xml'
    ],
    'images': ['static/description/banner.png',
               'static/description/icon.png',],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
