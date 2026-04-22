# -*- coding: utf-8 -*-
{
    'name': 'Bank Transfer',
    'summary': """Employee bank transfer""",
    'description': """
        This module allows employees to submit bank change requests.
        Features:
        - Pre-filled current bank data
        - New bank & IBAN validation
        - HR and Payroll Officer approvals
        - Supporting document uploads
        - Access control and activity scheduling
    """,
    'author': 'Kaizen',
    'website': 'https://www.kaizenae.com',
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['kaz_employees'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/bank_transfer_ir_sequence_data.xml',
        'data/bank_transfer_mail_activity_type_data.xml',
        'views/hr_employee_views.xml',
        'views/bank_transfer_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
