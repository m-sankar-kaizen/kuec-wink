# -*- coding: utf-8 -*-
{
    'name': "Employee Overtime",
    'summary': """ 
        Employee Overtime Management System
        Allows employees to submit overtime requests through a structured approval workflow involving line managers, HR, and directors.
    """,
    'description': """
        This module provides functionality to manage employee overtime requests. Key features include:
        - Multi-level approval workflow (Line Manager, HR, Director)
        - Domain-restricted employee selection based on user groups
        - Role-based access rules for security and control
        - Integrated with HR employee data from 'kaz_employees' module
        - Odoo chatter for communication and activity tracking
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['kaz_employees'],
    'data': [
        'security/employee_overtime_security.xml',
        'security/employee_overtime_rules.xml',
        'security/ir.model.access.csv',
        'views/employee_overtime_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
