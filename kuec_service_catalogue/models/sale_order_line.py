# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class SaleOrderLineBundle(models.Model):
    _inherit = 'sale.order.line'

    # WF-BND-001: employees per activation (stored on activated line)
    wink_selected_employee_ids = fields.Many2many(
        'kuec.employee.directory',
        'wink_sol_employee_rel',
        'sale_line_id',
        'employee_id',
        string='Activation Employees',
        help='Employees selected for this specific activation line. '
             'Used by WINK portal bundle workflow.',
    )

    wink_entitlement_wink_is_bundle = fields.Boolean(related='product_id.wink_is_bundle', store=True)
    wink_entitlement_id = fields.Many2one(
        'wink.bundle.entitlement',
        string='Bundle Entitlement',
        ondelete='set null',
        help='Links this activated line back to its bundle '
             'entitlement record.',
    )
    is_gov_charge_pending = fields.Boolean(
        string='Gov. Charges Pending',
        default=False,
        help='Flags this activation line as carrying government charges. '
             'Update the unit price to the confirmed government amount to make it invoiceable.',
    )

    def write(self, vals):
        """Notify the customer when coordinator confirms the gov charge amount.

        Workflow:
            1. Identify lines that are gov charge pending with price_unit currently 0.
            2. Run super().write(vals).
            3. For any such line that now has price_unit > 0, post a chatter
               message on the parent order so the customer is informed the
               amount has been confirmed and an invoice will follow.
        """
        pending_zero = {
            line.id
            for line in self
            if line.is_gov_charge_pending and line.price_unit == 0
        } if 'price_unit' in vals else set()

        result = super().write(vals)

        if pending_zero and vals.get('price_unit', 0) > 0:
            notified_orders = set()
            for line in self:
                if line.id in pending_zero and line.order_id.id not in notified_orders:
                    line.order_id.message_post(
                        body=_(
                            'Government charges confirmed: %(amount)s %(currency)s.\n'
                            'An invoice will be issued shortly.',
                            amount=line.price_unit,
                            currency=line.order_id.currency_id.name,
                        )
                    )
                    notified_orders.add(line.order_id.id)
        return result

    @api.depends('is_gov_charge_pending', 'price_unit')
    def _compute_qty_to_invoice(self):
        """Treat gov charge lines as order-policy once a price is set.

        Workflow:
            1. Run the standard qty_to_invoice computation via super().
            2. For any line flagged as gov charge pending with price > 0,
               override qty_to_invoice to product_uom_qty - qty_invoiced,
               making it immediately invoiceable regardless of delivery state.
        """
        super()._compute_qty_to_invoice()
        for line in self:
            if line.is_gov_charge_pending and line.price_unit > 0:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced


class SaleOrderConfirm(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Validate that bundled products are only purchased through
        the WINK bundle flow (with a tier selected), not added
        as standalone order lines.
        """
        for order in self:
            for line in order.order_line:
                if (line.product_id
                        and line.product_id.product_tmpl_id
                            .commercial_structure == 'bundled'
                        and not line.wink_entitlement_id
                        and not order.wink_bundle_tier_id):
                    is_bundled = (
                        self.env.context.get('is_bundle_line', False)
                        or (hasattr(line, 'linked_line_id')
                            and line.linked_line_id)
                    )
                    if not is_bundled:
                        raise ValidationError(_(
                            "'%(name)s' can only be purchased "
                            "as part of a bundle. It cannot be "
                            "added as a standalone order line."
                        ) % {'name': line.product_id.name})

        return super().action_confirm()
