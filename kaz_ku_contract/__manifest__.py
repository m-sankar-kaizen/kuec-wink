# -*- coding: utf-8 -*-
{
    'name': "KUEC Payroll/Contract",
    'summary': "Custom Payroll and HR Contract Enhancements for KUEC",
    'description': """
KUEC Payroll
============

This module provides payroll and HR contract customizations designed specifically for 
the Kuwait University Engineering College (KUEC) institutional requirements.

Features:
---------
- Customized HR contract views for KUEC.
- Payroll process integration with institutional policies.
- Extensible framework for future HR and payroll customizations.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Payroll',
    'version': '1.0',
    'depends': ['hr_payroll'],
    'data': [
        'views/hr_contract_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
