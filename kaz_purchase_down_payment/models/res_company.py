# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    po_deposit_default_product_id = fields.Many2one(
        'product.product',
        'PO Deposit Product',
        domain="[('type', '=', 'service')]",
        help='Default product used for payment advances in purchase order')