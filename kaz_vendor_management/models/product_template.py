# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_available_for_vendor_portal = fields.Boolean(
        string="Is Available For Vendor Portal",
        default=False,
        help="If enabled this product will be available to choose in the vendor registration "
             "portal under offered product/service section"
    )
