# -*- coding: utf-8 -*-
{
    'name': 'HR Housing Advance Management',
    'version': '1.0',
    'summary': 'Streamlined Employee Housing Advance Workflow',
    'description': """
        Empower HR teams with a continuous improvement-driven solution 
        to manage employee housing advances transparently and efficiently.
        Key Features:
            - Multi-level approval workflow
            - Eligibility based on grade and probation status
            - Payroll integration with automatic installment tracking
            - Configurable rules and HR-grade limits
            - Chatter support and activity tracking
    """,
    'category': 'Human Resources/Loan Management',
    'author': 'Kaizen Principles',
    'company': 'Kaizen Principles',
    'maintainer': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': [
        'account',
        'ent_hr_payroll_extension',
        'l10n_sa_hr_payroll',
        'kaz_employee_probation',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_refusal_data.xml',
        'data/loan_hr_salary_rule_data.xml',
        'data/loan_hr_salary_rule_data_2.xml',
        'data/hr_loan_ir_sequence_data.xml',
        'views/refuse_reason_views.xml',
        'views/hr_loan_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payslip_input_type_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payroll_structure_views.xml',
        'views/hr_grade_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}
