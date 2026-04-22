# -*- coding: utf-8 -*-
{
    'name': "Leave Entitlement (KUEC)",
    'description': """
This module extends Odoo HR Leave to introduce KUEC-specific leave entitlement rules.

Key Features:
• Define maximum number of days allowed per single leave request.
• Define yearly entitlement limits based on company policy.
• Validation rules to prevent exceeding daily or annual limits.
• Fully integrated with KUEC grade structure and company restriction logic.

Intended for organizations using KUEC leave policy requirements.
""",
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Purchases',
    'version': '1.0',
    'depends': ['hr_holidays', 'kaz_company_restriction_base', 'kaz_kuec_grade_structure'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
        'views/hr_religion_views.xml',
        'views/hr_employee_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
