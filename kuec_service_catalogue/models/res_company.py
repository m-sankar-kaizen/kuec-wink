# -*- coding: utf-8 -*-
# ISSUE-006: Company-specific reminder days for subscription expiry (no global ir.config_parameter for company-dependent config).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    wink_reminder_days_before = fields.Char(
        string='WINK Reminder Days (CSV)',
        help='Comma-separated days before subscription end to send a reminder (e.g. 30, 14, 7). '
             'Used when product has no override. Empty = use global default.'
    )
    wink_terms_html = fields.Html(
        string='WINK Terms & Conditions',
        sanitize=False,
        help='HTML content shown at /terms-and-conditions on the customer portal. '
             'Editable here or via Settings → Wink → Terms & Conditions.'
    )
