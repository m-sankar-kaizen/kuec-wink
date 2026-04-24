# -*- coding: utf-8 -*-
{
    'name': 'HR Internship Management',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Comprehensive internship management system with onboarding, rewards, feedback tracking, and compliance',
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'depends': ['hr', 'mail', 'hr_org_chart'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_config_parameter.xml',
        'views/internship_views.xml',
        'views/reward_views.xml',
        'views/feedback_views.xml',
        'views/orientation_views.xml',
        'views/freelance_deliverable_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
