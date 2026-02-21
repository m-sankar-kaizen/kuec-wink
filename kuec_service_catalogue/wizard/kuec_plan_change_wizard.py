# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date

class KuecPlanChangeWizard(models.TransientModel):
    _name = 'kuec.plan.change.wizard'
    _description = 'KUEC Upgrade/Downgrade/Cancellation Wizard'

    subscription_id = fields.Many2one('sale.order', string='Sale Order/Subscription', required=True)
    
    change_type = fields.Selection([
        ('upgrade', 'Upgrade'),
        ('downgrade', 'Downgrade'),
        ('cancel', 'Cancel with Refund')
    ], string='Action', required=True)

    current_product_id = fields.Many2one(
        'product.template', 
        string='Current Plan', 
        readonly=True,
        compute='_compute_current_product'
    )
    
    target_combo_id = fields.Many2one(
        'product.combo', 
        string='New Plan'
    )

    target_combo_domain = fields.Char(compute='_compute_target_domain')

    remaining_value = fields.Float(
        string='Remaining Value (Refundable)', 
        readonly=True,
        compute='_compute_remaining_value'
    )

    @api.depends('subscription_id')
    def _compute_current_product(self):
        for rec in self:
            if rec.subscription_id:
                # Get the first Wink service line on the subscription
                line = rec.subscription_id.order_line.filtered(
                    lambda l: l.product_id.product_tmpl_id.available_on_wink
                )[:1]
                rec.current_product_id = line.product_id.product_tmpl_id if line else False
            else:
                rec.current_product_id = False

    @api.depends('current_product_id', 'change_type')
    def _compute_target_domain(self):
        for rec in self:
            if not rec.current_product_id or rec.change_type == 'cancel':
                rec.target_combo_domain = '[]'
                continue
            
            group = rec.current_product_id.bundle_group_id
            if not group:
                rec.target_combo_domain = '[]'
                continue
            
            current_line = group.line_ids.filtered(
                lambda l: l.product_tmpl_id == rec.current_product_id
            )[:1]
            current_seq = current_line.sequence if current_line else 0
            
            if rec.change_type == 'upgrade':
                valid_lines = group.line_ids.filtered(lambda l: l.sequence > current_seq)
            else:  # downgrade
                valid_lines = group.line_ids.filtered(lambda l: l.sequence < current_seq)
            
            valid_combo_ids = valid_lines.mapped('combo_id').ids
            rec.target_combo_domain = str([('id', 'in', valid_combo_ids)])

    @api.depends('subscription_id', 'current_product_id')
    def _compute_remaining_value(self):
        for rec in self:
            try:
                # Assuming subscription_id has date_end or next_invoice_date in Odoo 18.
                # Assuming 'date_end' maps to the subscription renewal date. If it's pure standard Odoo 18 subscription, it might be next_invoice_date.
                # We will use next_invoice_date as a fallback for standard sales orders.
                end_date_field = getattr(rec.subscription_id, 'date_end', getattr(rec.subscription_id, 'next_invoice_date', False))
                if rec.subscription_id and rec.current_product_id and end_date_field:
                    group = rec.current_product_id.bundle_group_id
                    rec.remaining_value = group.compute_remaining_value(
                        rec.current_product_id,
                        end_date_field
                    )
                else:
                    rec.remaining_value = 0.0
            except UserError:
                rec.remaining_value = 0.0

    def action_confirm_plan_change(self):
        self.ensure_one()
        sub = self.subscription_id
        group = self.current_product_id.bundle_group_id
        remaining = self.remaining_value

        # Step 1: Issue credit
        if self.change_type != 'cancel' or remaining > 0:
            if group.credit_routing == 'gift_card':
                if not group.loyalty_program_id:
                    raise UserError(
                        "No Wallet/Gift Card Program configured "
                        "on the Bundle Group. Please set one "
                        "before processing a plan change."
                    )
                # Issue loyalty.card credit
                self.env['loyalty.card'].create({
                    'program_id': group.loyalty_program_id.id,
                    'partner_id': sub.partner_id.id,
                    'points': remaining,
                })
            else:
                # Issue credit note
                self.env['account.move'].create({
                    'move_type': 'out_refund',
                    'partner_id': sub.partner_id.id,
                    'invoice_line_ids': [(0, 0, {
                        'name': 'Plan Change Credit - %s' % self.current_product_id.name,
                        'price_unit': remaining,
                        'quantity': 1,
                    })],
                })

        # Step 2: Log chatter
        old_name = self.current_product_id.name
        new_name = self.target_combo_id.name if self.target_combo_id else 'N/A'
        sub.message_post(
            body=(
                "<b>Plan Change: %s</b><br/>"
                "Old Plan: %s<br/>"
                "New Plan: %s<br/>"
                "Remaining Value Credited: %.2f<br/>"
                "Credit Routing: %s"
            ) % (
                dict(self._fields['change_type'].selection).get(self.change_type),
                old_name,
                new_name,
                remaining,
                dict(group._fields['credit_routing'].selection).get(group.credit_routing),
            )
        )

        # Step 3: Close current subscription line and open new one (if upgrade/downgrade)
        if self.change_type != 'cancel':
            line = sub.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id == self.current_product_id
            )[:1]
            if line and self.target_combo_id:
                new_product = self.target_combo_id.combo_item_ids[:1].product_id
                if new_product:
                    line.product_id = new_product.id
        else:
            if hasattr(sub, 'action_cancel'):
                sub.action_cancel()

        return {'type': 'ir.actions.act_window_close'}
