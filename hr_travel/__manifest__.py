# -*- coding: utf-8 -*-
{
    'name': 'HR Travel Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Travel and errand management'
               ' with expense tracking and approvals',
    'author': 'KUEC',
    'depends': ['hr',
                'hr_expense',
                'kaz_annual_air_ticket',
                'kaz_kuec_grade_structure',
                'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/travel_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
