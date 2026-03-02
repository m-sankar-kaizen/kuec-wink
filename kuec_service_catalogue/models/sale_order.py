# -*- coding: utf-8 -*-
# ISSUE-006: Cron uses product → company → global reminder days; idempotent via wink_expiry_reminder_sent_days.

from odoo import models, fields, api
from datetime import date


def _parse_days_csv(value):
    """Parse comma-separated positive integers; return list."""
    if not value or not isinstance(value, str):
        return []
    return [int(d.strip()) for d in value.split(',') if d.strip().isdigit()]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_kuec_finalize_price(self):
        for order in self:
            order.wink_price_confirmed = True
            order.message_post(body="Service Coordinator unlocked this quote for payment on the portal.")

    @api.model
    def _cron_send_expiry_reminders(self):
        """
        Runs daily to find subscriptions nearing their end date and sends a reminder.
        Resolves reminder days: product override → company (res.company) → global default.
        Idempotent: does not re-send for the same remaining_days (uses wink_expiry_reminder_sent_days).
        """
        today = date.today()
        subscriptions = self.search([
            ('state', 'in', ['sale', 'done']),
            ('next_invoice_date', '!=', False)
        ])
        global_days_str = self.env['ir.config_parameter'].sudo().get_param(
            'kuec_service_catalogue.default_reminder_days', '30, 14, 7'
        )
        global_days = _parse_days_csv(global_days_str)

        for sub in subscriptions:
            remaining_days = (sub.next_invoice_date - today).days
            product = sub.wink_source_product_id
            if not product:
                continue
            # ISSUE-006: Resolve days in order product → company → global.
            product_days = product.reminder_days_before
            if product_days > 0:
                target_days = [product_days]
            else:
                company = sub.company_id
                company_str = company.wink_reminder_days_before if company else None
                target_days = _parse_days_csv(company_str) if company_str else global_days
            if remaining_days not in target_days:
                continue
            # Idempotency: already sent for this remaining_days?
            sent_str = sub.wink_expiry_reminder_sent_days or ''
            sent_set = set(_parse_days_csv(sent_str))
            if remaining_days in sent_set:
                continue
            template = self.env.ref(
                'kuec_service_catalogue.mail_template_kuec_subscription_expiry',
                raise_if_not_found=False
            )
            if template:
                template.send_mail(sub.id, force_send=True)
            sub.message_post(
                body=f"Subscription <b>Expiry Reminder</b> triggered automatically. Outstanding duration remains at {remaining_days} days."
            )
            sent_set.add(remaining_days)
            sub.wink_expiry_reminder_sent_days = ','.join(str(d) for d in sorted(sent_set))
