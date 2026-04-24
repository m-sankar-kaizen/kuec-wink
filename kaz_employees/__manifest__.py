# -*- coding: utf-8 -*-
{
    'name': "Employees Enhancement",
    'summary': "Enhancements and extensions to manage employee information and payroll-related configurations for KAZ.",
    'description': """
        This module extends the core HR and Payroll functionality to:
        - Add custom employee fields (units, sections, spouse, nationality, etc.)
        - Manage custom salary rules and payroll structure
        - Introduce grade and grade benefit management with automation
        - Include bank metadata extensions
        - Customize job, contract, and payslip views
        - Enable emergency and family member tracking
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['hr_payroll'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/salary_rule.xml',
        'data/ir_sequence.xml',
        'data/email_notification.xml',
        'data/ir_cron.xml',
        'views/hr_contract_views.xml',
        'views/hr_job_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_grade_views.xml',
        'views/hr_grade_benefit_views.xml',
        'views/unit_section_views.xml',
        'views/res_bank_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
