# -*- coding: utf-8 -*-
{
    'name': "Annual Air Ticket",
    'summary': "Annual Air Ticket Management for Employees",
    'description': """
        This module enables organizations to configure and manage the yearly air ticket 
        benefits provided to employees, including ticket types, pricing based on destination 
        and family members, ticket grants, and integration with payroll and HR.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Payroll',
    'version': '1.0',
    'depends': ['kaz_education_fees'],
    'data': [
        'data/ticket_ir_sequence.xml',
        'security/ir.model.access.csv',
        'views/res_destination_views.xml',
        'views/ticket_type_views.xml',
        'views/price_list_ticket_views.xml',
        'views/hr_employee_views.xml',
        'views/ticket_grant_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_grade_views.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'auto_install': False,
}
