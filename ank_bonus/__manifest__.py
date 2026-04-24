# -*- coding: utf-8 -*-
{
    'name': "Ankabut Bonus",
    'summary': """Bonus Analysis for Ku/Ankabut""",
    'description': """This module provides bonus analysis for Ku/Ankabut.""",
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['hr_payroll_account', 'wps_reports'],
    'data': [
        'data/hr_payroll_category.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_run_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
