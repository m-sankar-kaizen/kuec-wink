# -*- coding: utf-8 -*-
{
    'name': "HR Holidays",
    'summary': """Adds Director & CEO approval levels to Time Off Requests.""",
    'description': """
        This module enhances the Odoo Time Off module by introducing a 
        custom multi-level approval workflow. Features include:

        - Additional approval steps: Director and CEO
        - New status field `cycle_approve` shown as a statusbar
        - Custom buttons: 'Director' and 'CEO' for role-based validation
        - Permissions managed via custom user groups
        - View and button logic tailored to `hr.leave` form
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['hr_holidays'],
    'data': [
        'security/security.xml',
        'data/mail_activity_type_data.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'auto_install': False,
}
