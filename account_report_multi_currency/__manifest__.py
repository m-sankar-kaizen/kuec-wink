# -*- coding: utf-8 -*-
{
    'name': 'Account Reports Multi Currency',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Multi-currency support for financial/accounting reports.',
    'description': """
        Account Reports Multi Currency
        =================================
        This module extends the default Odoo Accounting Reports by allowing 
        users to generate financial reports (like balance sheet, P&L, trial balance) 
        in a selected currency that differs from the company’s base currency.

        Key Features:
        --------------
        - Add a toggle to enable/disable currency conversion.
        - Select a target currency for report display.
        - Currency-aware formatting for printed reports.
        - Enhanced user interface integration within accounting reports.

        Use Case:
        ----------
        Ideal for companies operating in multi-currency environments, 
        or for stakeholders needing financial summaries in a global currency 
        such as USD or EUR.

        """,
    'author': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'depends': ['account_reports'],
    'data': [
        'views/account_report_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'OPL-1',
}
