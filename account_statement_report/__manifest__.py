# -*- coding: utf-8 -*-
{
    'name': "Account Statement Report",
    'summary': "Generate detailed account statements for partners and accounts",
    'description': """
    Account Statement Report
    ========================
    This module provides a detailed account statement report for customers, vendors, and internal accounts.  
    It allows users to:
    - Generate partner-wise or account-wise statements.
    - Export statements in PDF format.

    Ideal for accountants and finance teams to analyze outstanding balances and transaction histories efficiently.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Accounting/Budget',
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'reports/account_statement.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
