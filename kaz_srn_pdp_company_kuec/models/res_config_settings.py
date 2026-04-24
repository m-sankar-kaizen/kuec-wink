# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """The class is to created for inherited the model Res Config Settings"""
    _inherit = 'res.config.settings'

    srn_report_template_id = fields.Many2one(
        related='company_id.srn_report_template_id', readonly=False)
