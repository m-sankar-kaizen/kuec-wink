# -*- coding: utf-8 -*-
from odoo import models, fields


class ResSettings(models.TransientModel):
    """
    Inherits from `res.config.settings` to make the requisition reminder
    configuration available in the General Settings interface.

    Uses related fields pointing to `res.company` to allow per-company configuration.
    Fields are editable (`readonly=0`) so that values can be saved through the UI.
    """

    _inherit = 'res.config.settings'

    requisition_first_reminder = fields.Integer(
        string='Requisition First Reminder (Days)',
        required=False,
        related='company_id.requisition_first_reminder',
        readonly=False,
        help="Number of days after the requisition date to send the first reminder.")

    requisition_days_reminder = fields.Integer(
        string='Requisition Reminder Interval (Days)',
        required=False,
        related='company_id.requisition_days_reminder',
        readonly=False,
        help="Interval in days for sending recurring reminders after the first one.")
