# -*- coding: utf-8 -*-
# ISSUE-006: Company-specific reminder days; global default remains fallback.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    kuec_default_reminder_days = fields.Char(
        string='Default Reminder Days (CSV)',
        config_parameter='kuec_service_catalogue.default_reminder_days',
        default='30, 14, 7',
        help="Global fallback: comma-separated days before expiry to send a reminder (e.g. '30, 14, 7'). "
             "Used when product and company have no override."
    )
    wink_company_reminder_days = fields.Char(
        related='company_id.wink_reminder_days_before',
        string='Company Reminder Days (CSV)',
        readonly=False,
        help="This company's reminder days (e.g. 30, 14, 7). Empty = use global default."
    )
