# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_code = fields.Selection('Company Code', related='company_id.company_code', readonly=True)
