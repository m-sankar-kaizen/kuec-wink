# -*- coding: utf-8 -*-

from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    kuec_default_reminder_days = fields.Char(
        string='Default Reminder Days (CSV)',
        config_parameter='kuec_service_catalogue.default_reminder_days',
        default='30, 14, 7',
        help="Comma-separated list of days before expiry to send a reminder (e.g. '30, 14, 7')."
    )
