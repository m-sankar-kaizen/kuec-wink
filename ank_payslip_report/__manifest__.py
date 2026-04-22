# -*- coding: utf-8 -*-
{
    'name': "Ankabut Payslip Report",
    'summary': """
        Customized payslip report with additional features for enhanced payroll management.
    """,
    'description': """
        This module provides a customized payslip report with additional features tailored for 
        payroll management. It includes improved layouts, additional fields, dual payslip 
        formats (ANK and KU), and better integration with WPS and payroll accounting.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['hr_payroll_account', 'wps_reports'],
    'data': [
        'reports/hr_payslip_report_action.xml',
        'views/hr_payslip_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ank_payslip_report/static/src/img/logo.jpeg',
        ],
    },
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
