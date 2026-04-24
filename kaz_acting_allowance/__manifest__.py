# -*- coding: utf-8 -*-
{
    'name': "Acting Allowance",
    'summary': """
        Manage employee acting allowances with multi-level approval.
    """,
    'description': """
        This module enables employees to request acting allowances when 
        assuming different job roles temporarily. It includes a structured 
        multi-stage approval workflow (Department Head → HR → CEO), 
        automatic allowance calculation, leave-based deductions, and contract integration.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Employee',
    'version': '1.0',
    'depends': ['ent_ohrms_loan'],
    'data': [
        'security/acting_allowance_security.xml',
        'security/acting_allowance_rules.xml',
        'security/ir.model.access.csv',
        'data/acting_allowance_ir_cron_data.xml',
        'data/acting_allowance_mail_template_data.xml',
        'views/employee_acting_allowance_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_grade_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
