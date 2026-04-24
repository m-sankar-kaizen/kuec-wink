# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attachment_expiry_reminder = fields.Integer(related='company_id.attachment_expiry_reminder',
                                                readonly=False)
