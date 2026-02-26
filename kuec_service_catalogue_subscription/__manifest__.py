# -*- coding: utf-8 -*-
{
    'name': 'KUEC Service Catalogue — Subscription Plan Fields',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Plan Features and Most Popular on product.pricing (Odoo 18 Subscription)',
    'description': """
    Extends product.pricing (from sale_subscription) with:
    - Plan Features (one per line) for portal display
    - Most Popular flag with one-per-product constraint
    Install this only when product.pricing exists in your Odoo (e.g. with sale_subscription).
    """,
    'author': 'Kaizen Options',
    'depends': [
        'kuec_service_catalogue',
        'sale_subscription',
    ],
    'data': [
        'views/product_pricing_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
