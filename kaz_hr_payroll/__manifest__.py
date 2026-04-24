# -*- coding: utf-8 -*-
{
    'name': "HR Payroll (Air Ticket Extension)",
    'summary': """Payroll extension with ticket grants, loans, and education reimbursements.""",
    'description': """
        This module extends the Odoo Payroll system with additional logic to 
        integrate seamlessly with other HR workflows such as:
        - Air Ticket Grants: Automatically mark related ticket lines as paid
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Payroll',
    'version': '1.0',
    'depends': ['kaz_ent_loan', 'kaz_annual_air_ticket'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
