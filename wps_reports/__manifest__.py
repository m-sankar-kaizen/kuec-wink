# -*- coding: utf-8 -*-
{
    'name': "WPS Reports",
    'summary': """
        Generate customized WPS-compliant payroll reports for employees.
    """,
    'description': """
        This module provides functionality to generate detailed payroll reports 
        that comply with the WPS (Wage Protection System) standards. It supports:
        - Exporting salary and allowance data in Excel format.
        - Integration with HR, Payroll, Leaves, and custom employee details.
        - Contract-based calculations and multi-company support.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Tools',
    'version': '1.0',
    'depends': ['kaz_employees', 'hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_contract_views.xml',
        'views/hr_assignment_category_views.xml',
        'views/hr_payslip_run_views.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
