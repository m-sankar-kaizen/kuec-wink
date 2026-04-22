# -*- coding: utf-8 -*-
{
    'name': "Three Level Time Off",
    'summary': "Adds a three-level approval flow for time off requests",
    'description': """
Three Level Time Off Approval
====================================

This module extends the Odoo Time Off application by introducing a three-step approval workflow:
1. Employee's Direct Manager
2. Time Off Officer
3. HR Manager

Key Features:
-------------
- New leave validation type: "three_level"
- Separate approval state for HR Manager
- Custom visibility and actions based on state and user roles
- Fully integrated with standard leave management

Developed by Kaizen Principles for Ankabut.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['hr_holidays'],
    'data': [
        'security/security.xml',
        'views/hr_leave_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
