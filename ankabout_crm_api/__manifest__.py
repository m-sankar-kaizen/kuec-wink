# -*- coding: utf-8 -*-
{
    'name': "Ankabut CRM API",
    'summary': "Expose CRM lead creation through an external API for Ankabut integration.",
    'description': """
This module enables API-based CRM lead creation in Odoo.It allows external systems 
(such as Ankabut portals or forms) to submit leads securely via token-authenticated 
JSON POST requests.
""",
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Sales/CRM',
    'version': '1.0',
    'depends': ['crm'],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}
