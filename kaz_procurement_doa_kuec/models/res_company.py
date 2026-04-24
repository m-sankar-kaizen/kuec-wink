# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    amount_po_without_pr = fields.Float(string='Amount PO without PR', digits=(16, 2), default=0,
                                        help='The max amount of a single PO that can be created without a PR')
