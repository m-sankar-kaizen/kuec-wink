# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lease_invoice_reminder_days = fields.Integer(
        related='company_id.lease_invoice_reminder_days',
        readonly=False,
        string='Lease Invoice Reminder Days',
        help='Number of days before lease invoice due date to send reminder notification'
    )
