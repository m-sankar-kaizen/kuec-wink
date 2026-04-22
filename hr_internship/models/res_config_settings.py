# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    reward_max_amount = fields.Monetary(related='company_id.reward_max_amount', readonly=False)
