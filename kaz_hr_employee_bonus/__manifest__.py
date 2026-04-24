# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Bonus',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Financial Awards and Annual Bonus Management',
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'depends': ['hr_payroll', 'account', 'mail', 'kaz_kuec_overall_doa_approval'],
    'data': [
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/financial_award_views.xml',
        'views/annual_bonus_views.xml',
        'views/financial_award_approval_views.xml',
        'views/annual_bonus_approval_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'auto_install': False,
}
