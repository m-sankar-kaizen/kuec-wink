# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    """
    Inherits from `res.company` to store requisition reminder configuration
    at the company level. These settings allow configuration of:
    - The day offset for the first requisition reminder.
    - The interval in days for subsequent reminders.
    """

    _inherit = 'res.company'

    requisition_first_reminder = fields.Integer(
        string='Requisition First Reminder (Days)',
        required=False,
        help="Number of days after the requisition date to trigger the first reminder.")

    requisition_days_reminder = fields.Integer(
        string='Requisition Reminder Interval (Days)',
        required=False,
        help="Number of days between subsequent reminders after the first reminder.")
