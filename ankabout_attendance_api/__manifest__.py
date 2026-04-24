# -*- coding: utf-8 -*-
{
    'name': "Attendance API",
    'summary': """
        Integration module for handling Ankabut attendance punch logs via secure API endpoints.
    """,
    'description': """
        This module enables attendance tracking integration with Ankabut systems via a secure REST API.
        It handles incoming punch data (check-in/check-out), maps employees using a token system,
        and logs attendance actions within Odoo's HR system.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['hr_attendance',
                'kaz_company_restriction_base',
                'kaz_employees'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menu_override.xml',
        'views/res_company_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/log_attendance_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
