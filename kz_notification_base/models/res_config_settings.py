# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """
    Extends the `res.config.settings` model to allow system administrators
    to set the SRN notification email at the company level via the Settings UI.

    This field is stored on the company (`res.company`) model but exposed
    in settings for convenience.

    Fields
    ------
    srn_notification_email : Char (related)
        Editable field bound to `company_id.srn_notification_email`, used to
        define or update the email address that receives SRN notifications.
    """
    _inherit = 'res.config.settings'

    srn_notification_email = fields.Char(
        string='SRN Notification Email',
        required=False,
        related='company_id.srn_notification_email',
        readonly=False,
        help="Set the email address that will receive SRN notifications. This value is stored per company."
    )
