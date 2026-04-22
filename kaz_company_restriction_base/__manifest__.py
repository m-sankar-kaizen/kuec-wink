# -*- coding: utf-8 -*-
{
    'name': "Company Restriction Base",
    'summary': "Provides a foundational framework for applying company-based access restrictions across Odoo modules.",
    'description': """
This module introduces the base structure required to implement company-level restriction logic across the system. 
It serves as a core dependency for current and future modules that need to enforce company-specific rules, visibility 
limitations, or access controls. By centralizing common restriction mechanisms, it ensures consistent and scalable 
company restriction behavior throughout the Odoo environment.
""",
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['base_setup'],
    'data': [
        'views/res_company_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
