# -*- coding: utf-8 -*-
{
    'name': 'HR Acting Delegation',
    'summary': 'Acting delegation of permissions during Time Off',
    'version': '1.0.0',
    'author': 'YourCompany',
    'depends': ['hr', 'hr_holidays', 'mail',
                'kaz_company_restriction_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/acting_delegation_views.xml',
        'views/hr_leave_views.xml',
        'wizards/acting_delegation_wizard_views.xml',
        'views/menu.xml',
    ],
    'application': False,
}
