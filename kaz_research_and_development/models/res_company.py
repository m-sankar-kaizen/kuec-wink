# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    r_and_d_max_financial_limit = fields.Float(string="Research & Development Financial Limit")
