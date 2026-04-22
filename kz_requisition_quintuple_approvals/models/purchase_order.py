# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    """
    Inherits `purchase.order` to introduce extended functionality for:
    - Linking purchase payments
    - Document attachments (scope of work, shareholders, board approval)
    - Requisition linkage and replacement tracking
    - Untaxed amount validations and partial PO bypass
    - Confirmation-level price variance validation against source requisition
    - Custom account move behavior for related POs
    """
    _inherit = "purchase.order"

    purchase_payment_ids = fields.One2many(
        comodel_name='account.payment',
        inverse_name='purchase_id',
        string='Payments Related to Purchase Order',
        required=False,
        help="Links all payments explicitly associated with this purchase order."
    )

    payments_count = fields.Integer(
        string='Number of Payments',
        required=False,
        compute='_compute_payments_count',
        help="Total number of payments related to this purchase order."
    )

    scope_of_work_attacchment_ids = fields.Many2many(
        'ir.attachment',
        'purchase_order_scope_attachment_rel',
        'purchase_id',
        'attach_id',
        string='Scope of Work Documents',
        help="Attachments for technical scope or project scope relevant to this PO."
    )

    shareholders_attacchment_ids = fields.Many2many(
        'ir.attachment',
        'purchase_shareholder_attachment_rel',
        'purchase_id',
        'attach_id',
        string='Shareholder Attachments',
        help="Attachments proving shareholder or ownership structure, if needed for compliance."
    )

    board_attacchment_ids = fields.Many2many(
        'ir.attachment',
        'purchase_board_attachment_rel',
        'purchase_id',
        'attach_id',
        string='Board Attachments',
        help="Board approval letters or meeting minutes supporting this purchase."
    )

    replaced_requisition_id = fields.Many2one(
        comodel_name='material.purchase.requisition',
        string='Replaced Requisition',
        help="Indicates this PO is a replacement for an older/invalid requisition."
    )

    @api.depends('purchase_payment_ids')
    def _compute_payments_count(self):
        """
        Compute the number of payment records linked to this purchase order.
        """
        for rec in self:
            rec.payments_count = len(rec.purchase_payment_ids)

    def show_purchase_payments(self):
        """
        Action to open a view displaying all payments linked to this purchase order.
        """
        return {
            'name': _('Payments'),
            'view_mode': 'list,form',
            'domain': [('purchase_id', '=', self.id)],
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
        }

    @api.constrains('amount_untaxed')
    def _restrict_amount(self):
        """
        Constraint to restrict creation of POs exceeding 2000 unless it's linked to a requisition
        or explicitly marked as a partial PO (`partial_po = True`).
        """
        for rec in self:
            if rec.amount_untaxed > 2000 and not rec.custom_requisition_id:
                if hasattr(self, 'partial_po') and getattr(self, 'partial_po'):
                    continue
                raise ValidationError(_("Not allowed to create an RFQ with amount exceeding 2000."))

    def write(self, vals):
        """
        Override to re-validate untaxed amount condition after updates.
        """
        res = super(PurchaseOrder, self).write(vals)
        self._restrict_amount()
        return res

    def button_confirm(self):
        """
        Override confirmation process to:
        - Validate price variance: if PO amount > 110% of requisition, halt and show a warning.
        - If acceptable, proceed with confirmation and cancel other RFQs related to the same requisition.
        """
        if self.custom_requisition_id and self.amount_untaxed > (1.1 * self.custom_requisition_id.total_amount):
            message = _("RFQ amount varies by more than 10% of the source requisition. Please resubmit for a new requisition or cancel.")
            wizard = self.env['purchase.confirmation.wizard'].create({
                'requisition_id': self.custom_requisition_id.id,
                'mode': 'reject',
                'purchase_id': self.id,
                'message': message
            })

            return {
                'name': 'Confirmation Warning',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.confirmation.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref('kz_requisition_quintuple_approvals.view_purchase_confirmation_wizard').id,
                'target': 'new',
                'res_id': wizard.id,
            }
        else:
            res = super(PurchaseOrder, self).button_confirm()
            self.cancel_related_rfqs()
            return res

    def cancel_related_rfqs(self):
        """
        Cancel all other POs linked to the same requisition except the current one.
        Used to enforce single PO execution per requisition.
        """
        if self.custom_requisition_id and self.custom_requisition_id.purchase_ids:
            for purchase in self.custom_requisition_id.purchase_ids:
                if purchase.id != self.id:
                    purchase.button_cancel()

    def action_show_replacement(self):
        """
        Returns an action to open the form view of the replaced requisition, if any.
        """
        self.ensure_one()
        requisition_action = self.env['ir.actions.act_window']._for_xml_id(
            'material_purchase_requisitions.action_material_purchase_requisition')
        requisition_action.update({
            'res_id': self.replaced_requisition_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(self.env.ref('material_purchase_requisitions.material_purchase_requisition_form_view').id, 'form')],
            'target': 'current',
        })
        return requisition_action

    def prepare_compare_quantities(self, done=False):
        """
        Helper method to build a dictionary of product quantities and price units for comparison.
        Used in PO vs requisition analytics.
        """
        quantities_dict = {}
        price_dict = {}
        for line in self.order_line:
            quantities_dict[line.product_id.id] = quantities_dict.get(line.product_id.id, 0) + line.product_qty
            price_dict[line.product_id.id] = price_dict.get(line.product_id.id, 0) + line.price_unit
        return [quantities_dict, price_dict]

    @api.onchange('currency_id', 'company_id')
    def _onchange_currency_id_set_manual_rate(self):
        """
        When the currency or company changes, suggest the standard
        conversion rate in the manual rate field.
        """
        rate = self.expected_currency_rate
        if self.custom_requisition_id and self.custom_requisition_id.currency_id != self.custom_requisition_id.company_currency_id:
            rate = self.custom_requisition_id.purchase_manual_currency_rate

        self.purchase_manual_currency_rate = rate


class PurchaseOrderLine(models.Model):
    """
    Inherits `purchase.order.line` to allow assigning custom expense account
    for each individual PO line, used in accounting entry override.
    """
    _inherit = "purchase.order.line"

    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        required=False,
        help="Optional override account for this PO line. Used during invoice line generation."
    )
    custom_requisition_id = fields.Many2one(related='order_id.custom_requisition_id')

    def _prepare_account_move_line(self, move=False):
        """
        Override to apply the `account_id` set at PO line level into the journal entry.
        """
        res = super()._prepare_account_move_line(move)
        if self.account_id:
            res.update({'account_id': self.account_id.id})
        return res
