# -*- coding: utf-8 -*-
{
    'name': "Pension Report",
    'summary': """
        Generate detailed UAE & GCC pension reports based on payroll data
        for local and GCC-national employees as per government requirements.
    """,
    'description': """
        This module provides functionality to generate pension report Excel files
        for submission to the Abu Dhabi Retirement Pensions and Benefits Fund (ADRPBF).
        
        Features:
        - Extracts employee-wise data from payroll (payslip runs).
        - Generates GCC pension reports for employees from Bahrain, Kuwait, Oman, Qatar, and Saudi Arabia.
        - Generates UAE-specific pension reports for local employees.
        - Includes key salary components like basic, allowances, shares, and totals.
        - Supports formatted Excel export with totals and structured layout.
        - Files are generated as attachments and made downloadable via browser.

        Dependencies:
        - `kaz_employees`: for accessing custom employee fields like `ku_number`, `kaz_employee_type`, etc.
        - `hr_holidays`: required for integrating with standard HR payroll structure.

        Target Users:
        - Payroll Officers
        - HR Managers
        - Finance Departments
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['kaz_employees', 'hr_holidays'],
    'data': [
        'views/hr_payslip_run_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
