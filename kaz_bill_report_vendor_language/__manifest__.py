# -*- coding: utf-8 -*-
{
    'name': 'Bill Report By Vendor Language',
    'summary': "Generate Vendor Bills in the Vendor's Preferred Language (Currently Arabic Only)",
    "description": """
    Bill Report by Vendor Language
    ==============================

    This module customizes the vendor bill/invoice report to be printed in the vendor's preferred language.

    Features:
    ---------
    - Automatically generate bill reports in the vendor's language.
    - Currently supports **Arabic translation** for vendor bills.
    - Ensures better communication and localization for Arabic-speaking vendors.
    - Seamless integration with Accounting and Invoicing modules.

    """,
    'author': 'Kaizen',
    'website': 'https://www.kaizenae.com',
    'category': 'Extra Tools',
    'version': '1.0',
    'depends': ['l10n_gcc_invoice'],
    'data': [
        'reports/account_move_invoice_template.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    "auto_install": False,
    "application": False,
}
