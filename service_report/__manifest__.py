# -*- coding: utf-8 -*-
{
    'name': 'Service Order Report - Purchase',
    'summary': 'Custom Service Order print report and form extension for Purchase Orders.',
    'description': """
        Service Order Report - Purchase
        This module extends the Purchase module by:

        - Adding additional fields to the purchase order form to support Service Order workflows.
        - Including fields such as Service Order Title, Contract Reference, Effective Date, and End Date.
        - Generating a structured, multi-section Service Order PDF report with embedded Terms & Conditions.
        - Supporting contractor contact info, pricing breakdown, and approval signatures.

        Intended for government and enterprise use cases with detailed service agreements.
    """,
    'author': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['purchase', 'hr'],
    'data': [
        'views/purchase_order_views.xml',
        'reports/service_order_report.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
