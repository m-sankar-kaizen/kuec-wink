# -*- coding: utf-8 -*-
{
    'name': "Loan Management",
    'summary': "Extended workflow, deduction tracking, and visual status for enterprise loan management",
    'description': """
    Enhanced Loan Management Module

    This module extends the capabilities of the standard Odoo HR Loan Management apps 
    (`ent_ohrms_loan` and `ent_loan_accounting`) by introducing:

    ✔ Multi-level loan approval workflow:
        - Draft → HR Team → Branch Manager → HR Manager → Approval/Refusal
        - Controlled access via user groups

    ✔ Visual ribbon for granted loans to improve loan status clarity

    ✔ Dynamic housing loan deduction handling via contracts and payslips

    ✔ Mail activity integration to notify appropriate approvers

    ✔ Enforcement of business rules on loan amount, installments, and exclusivity

    Key Features:
    - Additional loan states with fine-grained role separation
    - Auto-detection of housing advances in contracts
    - Prevents duplicate loan approvals or excessive loan amounts
    - Enhanced form view buttons and statusbar
    - Automated loan-related mail activities (reminders)

    Dependencies:
    - `ent_ohrms_loan`: Base enterprise loan functionality
    - `ent_loan_accounting`: Loan installment accounting integration

    Intended Users:
    - HR Officers
    - Payroll Managers
    - Branch Managers
    - Super Admins
        """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Loan Management',
    'version': '1.0',
    'depends': ['ent_loan_accounting'],
    'data': [
        'data/mail_activity_type_data.xml',
        'views/hr_loan_views.xml',
        'views/hr_contract_views.xml'
    ],
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'auto_install': False,
}
