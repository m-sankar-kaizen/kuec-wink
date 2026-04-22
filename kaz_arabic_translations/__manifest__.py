# -*- coding: utf-8 -*-
{
    'name': "Arabic Translations",
    'summary': """Arabic Translations""",
    'description': """
        Arabic Translations: Adds Arabic translations for employee name, job position, department, 
        and nationality. Install the module and ensure Arabic language is enabled in the system.
    """,
    'author': "kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Tools',
    'version': '1.0',
    'depends': ['hr'],
    'data': [
        'views/hr_employee_views.xml',
        'views/hr_employee_public_views.xml',
        'views/hr_job_views.xml',
        'views/hr_department_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_post_install_arabic_language',
}
