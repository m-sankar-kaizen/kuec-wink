# -*- coding: utf-8 -*-
# ISSUE-006: Cron uses product → company → global reminder days; idempotent via wink_expiry_reminder_sent_days.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


def _parse_days_csv(value):
    """Parse comma-separated positive integers; return list."""
    if not value or not isinstance(value, str):
        return []
    return [int(d.strip()) for d in value.split(',') if d.strip().isdigit()]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_pending_gov_charges = fields.Boolean(
        compute='_compute_has_pending_gov_charges',
        string='Has Pending Gov Charges',
        help='True when at least one order line has government charges pending (price = 0).',
    )

    @api.depends('order_line.is_gov_charge_pending', 'order_line.price_unit')
    def _compute_has_pending_gov_charges(self):
        for order in self:
            order.has_pending_gov_charges = any(
                line.is_gov_charge_pending and line.price_unit == 0
                for line in order.order_line
            )

    def action_confirm(self):
        """EPIC-11: After confirming a WINK portal order, enable customer ratings
        on the auto-created project so evaluations are sent when tasks close.
        Also ensures all folded stages of the project have rating_template_id set
        so Odoo actually dispatches the email.

        Also blocks confirmation of portal requests that have not been finalized
        (wink_price_confirmed=False) to prevent accidental confirmation before
        the coordinator has set and unlocked the pricing for the customer.
        """
        for order in self:
            if order.wink_is_portal_request and not order.wink_price_confirmed:
                raise UserError(_(
                    'Cannot confirm "%s": please click "Finalize & Unlock Payment" first '
                    'to set the price and notify the customer before confirming.',
                    order.name,
                ))
        result = super().action_confirm()
        # Use WINK custom template — hides vendor name from customer
        rating_template = self.env.ref(
            'kuec_service_catalogue.mail_template_wink_rating_request',
            raise_if_not_found=False,
        ) or self.env.ref(
            'project.rating_project_request_email_template',
            raise_if_not_found=False,
        )
        for order in self:
            if not order.wink_is_portal_request:
                continue
            # Search project directly — tasks may not exist yet at confirmation time
            projects = self.env['project.project'].sudo().search([
                ('sale_order_id', '=', order.id),
            ])
            # Fallback: find via tasks in case sale_order_id is on tasks only
            if not projects:
                projects = self.env['project.task'].sudo().search([
                    ('sale_order_id', '=', order.id),
                ]).mapped('project_id').filtered(lambda p: p)
            if not projects:
                continue
            projects.filtered(lambda p: not p.rating_active).write({
                'rating_active': True,
                'rating_status': 'stage',
            })
            # Ensure every folded stage of the project has a rating template so
            # that _send_task_rating_mail() actually dispatches the email.
            if rating_template:
                folded_stages = projects.mapped('type_ids').filtered(
                    lambda s: s.fold and not s.rating_template_id
                )
                if folded_stages:
                    folded_stages.sudo().write({'rating_template_id': rating_template.id})
        return result

    def action_kuec_finalize_price(self):
        """Open the Finalize & Unlock Payment wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Finalize & Unlock Payment',
            'res_model': 'wink.finalize.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

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
                body=_(
                    'Subscription Expiry Reminder triggered automatically. '
                    'Outstanding duration remains at %(days)s days.',
                    days=remaining_days,
                )
            )
            sent_set.add(remaining_days)
            sub.wink_expiry_reminder_sent_days = ','.join(str(d) for d in sorted(sent_set))
