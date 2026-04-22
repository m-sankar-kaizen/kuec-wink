# -*- coding: utf-8 -*-
{
    'name': "Restrict Product Types",
    'summary': """Restricts product creation to only 'Service' or 'Consumable' types.""",
    'description': """
        This module extends the Product Template model to enforce a validation constraint
        that limits product creation and modification to only two allowed types:
        - Consumable (`consu`)
        - Service (`service`)

        Attempts to set the product type as 'Stockable Product' (`product`) or any
        other type will result in a validation error.

        This is especially useful for service-based businesses or companies that do
        not manage stock in Odoo and want to enforce data consistency in product setup.
    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Inventory/Inventory',
    'version': '1.0',
    'depends': ['product'],
    'license': 'LGPL-3',
    'application': False,
    'installable': True,
    'auto_install': False,
}
