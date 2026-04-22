# -*- coding: utf-8 -*-
"""
This module extends the `res.company` and `res.config.settings` models to introduce
a configurable company-level email field named `srn_notification_email`. This field is intended
to be used for sending system-related notifications such as SRN (System Reference Number) alerts
or similar events requiring email dispatch to a fixed address.
"""
from odoo import api, fields, models, _


class ResCompany(models.Model):
    """
    Inherits the standard `res.company` model to add a field for storing
    a company-specific notification email address used for SRN alerts or other
    similar automated notifications.

    Fields
    ------
    srn_notification_email : Char
        The email address that should receive SRN notifications for this company.
    """
    _inherit = 'res.company'

    srn_notification_email = fields.Char(
        string='SRN Notification Email',
        required=False,
        help="Email address that will receive automated SRN notifications for this company."
    )


