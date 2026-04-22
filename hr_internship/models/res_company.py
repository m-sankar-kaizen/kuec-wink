# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    reward_max_amount = fields.Monetary(string='Maximum Reward Amount', default=10000)
