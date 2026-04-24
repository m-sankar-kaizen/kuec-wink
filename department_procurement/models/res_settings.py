from odoo import models, fields
import calendar


class ResSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    notification_month = fields.Selection(
        related='company_id.notification_month',
        readonly=False)
    notification_day = fields.Integer(
        related='company_id.notification_day',
        readonly=False)
