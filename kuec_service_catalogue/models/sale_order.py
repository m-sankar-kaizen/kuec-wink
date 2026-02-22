# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta

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
            # Optional: Log message to chatter
            order.message_post(body="Service Coordinator unlocked this quote for payment on the portal.")

    def action_kuec_open_plan_change_wizard(self):
        self.ensure_one()
        
        # In a real context, we open the wizard for the "primary" subscription line 
        # For MVP, we'll pick the first bundle line.
        active_line = self.order_line.filtered(
            lambda l: l.product_template_id.commercial_structure == 'bundled' and l.state in ['sale', 'done']
        )[:1]

        return {
            'name': 'Subscription Plan Change',
            'type': 'ir.actions.act_window',
            'res_model': 'kuec.plan.change.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_current_product_id': active_line.product_template_id.id if active_line else False,
            }
        }

    @api.model
    def _cron_send_expiry_reminders(self):
        """
        Runs daily to find subscriptions nearing their end date and sends a reminder.
        Matches the days remaining against `product.template.reminder_days_before`
        or the global setting `kuec_service_catalogue.default_reminder_days`.
        """
        today = date.today()
        # Find all active subscriptions that have an end date set
        subscriptions = self.search([
            ('state', 'in', ['sale', 'done']), 
            ('next_invoice_date', '!=', False) # Assuming Odoo uses this or 'end_date'
        ])

        global_days_str = self.env['ir.config_parameter'].sudo().get_param('kuec_service_catalogue.default_reminder_days', '30, 14, 7')
        global_days = [int(d.strip()) for d in global_days_str.split(',') if d.strip().isdigit()]

        # Process each subscription
        for sub in subscriptions:
            # For MVP logic, track via the first bundled line product, 
            # normally this links directly to the `plan_id` or similar subscription construct.
            active_line = sub.order_line.filtered(lambda l: l.product_template_id.commercial_structure == 'bundled')[:1]
            if not active_line:
                continue
                
            product = active_line.product_template_id
            product_days = product.reminder_days_before

            # Calculate days remaining
            remaining_days = (sub.next_invoice_date - today).days
            
            # Check if today is an exact hit for a reminder day marker
            needs_reminder = False
            if product_days > 0 and remaining_days == product_days:
                needs_reminder = True
            elif product_days == 0 and remaining_days in global_days:
                needs_reminder = True

            if needs_reminder:
                # Send Email
                template = self.env.ref('kuec_service_catalogue.mail_template_kuec_subscription_expiry', raise_if_not_found=False)
                if template:
                    template.send_mail(sub.id, force_send=True)
                    
                # Log Chatter
                sub.message_post(
                    body=f"Subscription <b>Expiry Reminder</b> triggered automatically. Outstanding duration remains at {remaining_days} days."
                )
