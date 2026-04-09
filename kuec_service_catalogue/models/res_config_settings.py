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
    wink_terms_html = fields.Html(
        related='company_id.wink_terms_html',
        string='WINK Terms & Conditions',
        readonly=False,
        sanitize=False,
        help='HTML content shown at /terms-and-conditions on the customer portal.'
    )
    wink_gov_charge_product_id = fields.Many2one(
        related='company_id.wink_gov_charge_product_id',
        string='Government Charges Product',
        readonly=False,
        help='Global product used for all government charge lines on sale orders.',
    )
    wink_expense_journal_id = fields.Many2one(
        related='company_id.wink_expense_journal_id',
        string='Promotional Credit Expense Journal',
        readonly=False,
        domain=[('type', '=', 'general')],
        help='Default journal for Promotional Credit top-up expense entries.',
    )
