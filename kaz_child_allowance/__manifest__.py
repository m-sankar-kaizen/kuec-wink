# -*- coding: utf-8 -*-
{
    'name': "Child Allowance",
    'summary': "Manage Child Allowance Requests, Approvals, Eligibility, and Payroll Integration",
    'description': """
Child Allowance
===================

This module provides a structured process to manage employee child allowance benefits:

Features:
---------
- Submit and track child allowance requests.
- Attach supporting documents for verification.
- Route requests through line manager and HR manager approval workflows.
- Monitor payment and allowance status.
- Automatically compute allowances in payroll based on eligible children.
- Reflect allowance details on employee contracts and payslips.

Use Cases:
----------
- Government organizations, universities, or HR departments requiring structured benefit management.
- Automates compliance and ensures consistency in allowance eligibility and payments.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Employee',
    'version': '1.0',
    'depends': ['kaz_annual_air_ticket'],
    'data': [
        'security/child_allowance_security.xml',
        'security/ir.model.access.csv',
        'views/child_allowance_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_contract_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
