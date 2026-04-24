# -*- coding: utf-8 -*-
{
    'name': 'Leave Day Type Customization',
    'summary': 'Enhances leave management by allowing leave types to be configured '
               'to count leave in either calendar days or working days, providing '
               'flexibility in leave duration calculations aligned with organizational'
               ' policies.',

    'description': """
        This module extends the standard Odoo leave management system by
         introducing the option to define how leave days are calculated for
          each leave type. Users can specify whether the leave duration is
           counted based on calendar days (including weekends and holidays) 
           or working days (excluding non-working days).
        
        Key Features:
        - Add a 'Day Calculation Type' field to leave types with two options: 
        'Working Days' and 'Calendar Days'.
        - Allows accurate leave duration calculation in reports and validations
         depending on organizational leave policies.
        - Seamless integration with existing leave workflows.
        - Improves clarity and flexibility for HR teams managing diverse leave types.
        
        Use Cases:
        - Organizations that want leave like sick leave to be counted as calendar days.
        - Leave types such as annual leave or vacation calculated on working days only.
        - Compliance with company or regional labor regulations for leave counting.

        This module depends on the 'hr_holidays' and 'resource' modules to 
        leverage existing attendance and calendar functionality.
    """,
    'author': 'Kaizen',
    'website': 'http://www.kaizenae.com',
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['hr_holidays', 'resource', 'hr_payroll'],
    'data': [
        'views/hr_leave_type_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
