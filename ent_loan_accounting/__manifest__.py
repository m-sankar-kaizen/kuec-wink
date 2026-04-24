# -*- coding: utf-8 -*-
{
    'name': 'Loan Accounting',
    'version': '1.0',
    'summary': 'Seamless Accounting Integration for Employee Loans in Open HRMS',
    'description': """
        Enterprise Loan Accounting Extension for Open HRMS

        Kaizen Principles Applied:
        - **Process Visibility**: Integrates loan approval with accounting for complete traceability.
        - **Standardization**: Automates journal entries for loan disbursement and repayments.
        - **Empowerment**: Enables HR and Finance collaboration through configurable multi-level approvals.
        - **Simplicity**: Minimizes manual effort by connecting loan records with payroll and accounting flows.

        Features:
        - Generates journal entries when loans are approved by accounting.
        - Adds final loan approval stage for accountants (post-HR approval).
        - Loan approval setting toggle in accounting configuration (Settings).
        - Extends HR loan form with enhanced workflow and statusbar.
        - Posts loan installment deductions via payslip validation.

        Suitable For:
        - Corporates with centralized or finance-audited loan policies.
        - Organizations using both HR and Accounting modules in Odoo Enterprise.

        Related Modules:
        - `ent_ohrms_loan`: Required for employee loan workflow.
        - `ent_hr_payroll_extension`: Ensures compatibility with payroll deductions.
    """,
    'category': 'Human Resources/Loan Management',
    'author': "Kaizen Principles",
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': "https://www.kaizenae.com",
    'depends': [
        'account_accountant',
        'ent_ohrms_loan'
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/hr_loan_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}
