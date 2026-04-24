# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    br_sale_lock_day = fields.Integer(
        related="company_id.br_sale_lock_day", readonly=False)
    br_purchase_lock_day = fields.Integer(
        related="company_id.br_purchase_lock_day", readonly=False)
    br_gl_lock_day = fields.Integer(
        related="company_id.br_gl_lock_day", readonly=False)
    br_lock_mode = fields.Selection(
        related="company_id.br_lock_mode", readonly=True)
