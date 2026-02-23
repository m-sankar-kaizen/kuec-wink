# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    wink_price_confirmed = fields.Boolean(
        string='Wink Price Confirmed',
        default=False,
        help='If checked, hidden price services on this order are finalized and ready for portal checkout.'
    )

    def action_kuec_finalize_price(self):
        for order in self:
            order.wink_price_confirmed = True
            order.message_post(body="Service Coordinator unlocked this quote for payment on the portal.")

    @api.model
    def _cron_send_expiry_reminders(self):
        """
        Runs daily to find subscriptions nearing their end date and sends a reminder.
        Matches the days remaining against `product.template.reminder_days_before`
        or the global setting `kuec_service_catalogue.default_reminder_days`.
        """
        today = date.today()
        subscriptions = self.search([
            ('state', 'in', ['sale', 'done']),
            ('next_invoice_date', '!=', False)
        ])

        global_days_str = self.env['ir.config_parameter'].sudo().get_param('kuec_service_catalogue.default_reminder_days', '30, 14, 7')
        global_days = [int(d.strip()) for d in global_days_str.split(',') if d.strip().isdigit()]

        for sub in subscriptions:
            remaining_days = (sub.next_invoice_date - today).days
            product = sub.wink_source_product_id
            if not product:
                continue

            product_days = product.reminder_days_before

            needs_reminder = False
            if product_days > 0 and remaining_days == product_days:
                needs_reminder = True
            elif product_days == 0 and remaining_days in global_days:
                needs_reminder = True

            if needs_reminder:
                template = self.env.ref('kuec_service_catalogue.mail_template_kuec_subscription_expiry', raise_if_not_found=False)
                if template:
                    template.send_mail(sub.id, force_send=True)

                sub.message_post(
                    body=f"Subscription <b>Expiry Reminder</b> triggered automatically. Outstanding duration remains at {remaining_days} days."
                )
