# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    lease_invoice_reminder_days = fields.Integer(
        string='Lease Invoice Reminder Days',
        default=7,
        help='Number of days before lease invoice due date to send reminder notification'
    )
