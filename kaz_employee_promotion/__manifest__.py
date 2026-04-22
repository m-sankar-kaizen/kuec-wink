# -*- coding: utf-8 -*-
{
    'name': "Employee Promotion",
    'version': '1.0',
    'summary': 'Manage employee promotions and promotion history',
    'description': """
    Employee Promotion Module

    This module allows HR managers to handle employee promotions efficiently. 
    It provides functionalities to:
    - Record promotion requests
    - Define promotion types
    - Track promotion history for each employee
    - Generate promotion reports and templates
    - Integrate with HR contracts and employee records
    """,
     'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'depends': ['mail', 'hr_contract'],
    'data': [
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'views/employee_promotion_views.xml',
        'views/promotion_type_views.xml',
        'views/hr_employee_views.xml',
        'report/employee_promotion_report.xml',
        'report/employee_promotion_templates.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
