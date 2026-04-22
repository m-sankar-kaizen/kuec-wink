# -*- coding: utf-8 -*-
{
    'name': "Sales Invoice Report",
    'summary': """
        Custom printable Tax Invoice report for Sales Invoices (account.move)""",
    'description': """
        This module provides a customized PDF Tax Invoice layout for customer invoices in Odoo,
        with a professional design including company logo, VAT details, bank account information,
        and customer-specific billing sections.

        Features:
        - Custom report template for account.move (Invoices)
        - Bank details and authorized signature
        - Customer and invoice metadata
        - Multi-language currency amount in words
        - VAT registration display
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'reports/sale_invoice_report.xml',
    ],
    'post_init_hook': 'install_es_ar_lang',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
