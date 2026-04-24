# -*- coding: utf-8 -*-
{
    'name': "Recruitment",
    'summary': """Employee Recruitment""",
    'description': """ Employee Recruitment """,
    'author': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['kaz_employees',
                'website_hr_recruitment',
                'documents_hr_recruitment',
                'kaz_company_restriction_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/email_notification.xml',
        'views/hr_job_views.xml',
        'views/hr_recruitment_stage_views.xml',
        'security/security.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
