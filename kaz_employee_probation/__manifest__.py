# -*- coding: utf-8 -*-
{
    'name': "Employee Probation",
    'summary': "Configure and manage probation periods for Expat and Local employees",
    'description': """
Kaz Employee Probation

This module allows HR managers and administrators to:
- Configure company-specific probation periods (in months) for both Expat and Local employees.
- Automatically compute and display the number of remaining probation days on employee records.
- Run a scheduled cron job to update probation status once the probation period ends.

Key Features:
- Extend `hr.employee` model with probation tracking fields.
- Add settings in company configuration to define probation periods.
- Cron job (`check_probation`) evaluates and updates the `is_under_probation` flag.
- User-friendly interface integration in employee form and settings views.

Intended Users:
- HR Managers
- HR Officers
- System Administrators
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Employees',
    'version': '1.0',
    'depends': ['kaz_employees',
                'kaz_company_restriction_base'],
    'data': [
        'data/probation_end_ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
