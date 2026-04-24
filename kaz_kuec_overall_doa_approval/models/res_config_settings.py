# -*- coding: utf-8 -*-
from odoo import fields, api, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ceo_job_id = fields.Many2one(related='company_id.ceo_job_id', string='CEO Job', readonly=False)
