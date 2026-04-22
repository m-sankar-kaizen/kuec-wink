# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    r_and_d_max_financial_limit = fields.Float(related='company_id.r_and_d_max_financial_limit', readonly=False)
