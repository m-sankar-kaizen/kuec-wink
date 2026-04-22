# -*- coding: utf-8 -*-
{
    'name': 'Payment Provider: N-Genius',
    'version': '18.0.1.0.1',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': 'N-Genius Online Hosted Payment Page integration for the GCC/MENA region.',
    'description': ' ',  # Non-empty string to suppress README auto-loading by Odoo.
    'author': 'Kaizen Options',
    'depends': ['payment'],
    'data': [
        'views/payment_ngenius_templates.xml',
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',  # Must load after views/payment_ngenius_templates.xml
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
