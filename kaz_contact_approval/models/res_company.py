# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    attachment_expiry_reminder = fields.Integer(
        string='Attachment Expiry Reminder (Days)',
        help='Number of days before an attachment expires when a notification '
             'should be sent to responsible users.'
    )