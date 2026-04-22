# -*- coding: utf-8 -*-
from odoo import fields, api, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    amount_po_without_pr = fields.Float(related='company_id.amount_po_without_pr',
                                        string='Amount PO without PR', readonly=False)
