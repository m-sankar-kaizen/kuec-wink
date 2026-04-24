# -*- coding: utf-8 -*-
{
    'name': 'Hide Menu Company wise',

    'summary': """
           Hide Menu Company wise
        """,

    'description': """
        Hide Menu Company wise
    """,
    'author': 'NextGen Odoo Solutions',
    'company': 'NextGen Odoo Solutions',
    'maintainer': 'NextGen Odoo Solutions',
    'website': 'https://nextgen-odoo-solutions.odoo.com/',
    'version': '1.0',
    'category': 'Service',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'views/res_company_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 9,
    'currency': 'USD',
    'images': ['static/description/banner.png'],
    'sequence': 50,

}
