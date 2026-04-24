# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """The class is to created for inherited the model Res Config Settings"""
    _inherit = 'res.config.settings'

    po_deposit_default_product_id = fields.Many2one(
        related='company_id.po_deposit_default_product_id', readonly=False)
