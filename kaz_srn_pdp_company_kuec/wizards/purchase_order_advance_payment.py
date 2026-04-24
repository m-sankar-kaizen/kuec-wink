# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class PurchaseOrderAdvancePayment(models.TransientModel):
    _inherit = 'purchase.order.advance.payment'

    letter_of_guarantee = fields.Binary('LG / Bank Letter', help="Letter of guarantee")

    def action_create_advance_bill(self):
        """Function for creating purchase down payment bill"""
        purchase_order = self.env['purchase.order'].browse(
            self._context.get('active_ids', []))
        if self.advance_payment_method == 'delivered':
            if self.deduct_down_payments:
                purchase_order._deduct_payment(final=self.deduct_down_payments)
            else:
                purchase_order.action_create_invoice()
        else:
            if not self.product_id:
                raise UserError(
                    _("Please configure the default down payment product in the settings."))
            purchase_line_obj = self.env['purchase.order.line']
            for order in purchase_order:
                amount, name = self._get_advance_details(order)
                if self.product_id.invoice_policy != 'order':
                    raise UserError(
                        _('The product used to invoice a down payment should '
                          'have an invoice policy set to "Ordered '
                          'quantities". Please update your deposit product to '
                          'be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(
                        _("The product used to invoice a down payment should "
                          "be of type 'Service'. Please use another product "
                          "or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda
                        r: not order.company_id or r.company_id == order.company_id)
                tax_ids = order.fiscal_position_id.map_tax(taxes).ids
                po_line_values = self._prepare_po_line(order, tax_ids, amount)
                po_line = purchase_line_obj.with_context(no_srn=True).create(po_line_values)
                self._create_bill(order, po_line, amount)
                if self.letter_of_guarantee:
                    self.env['ir.attachment'].create({
                        'name': 'Letter of Guarantee',
                        'res_model': 'purchase.order',
                        'res_id': order.id,
                        'type': 'binary',
                        'datas': self.letter_of_guarantee,
                        'mimetype': 'application/pdf',
                    })
                    order.message_post(body=_("Letter of Guarantee has been attached."))
                if self._context.get('open_invoices', False):
                    return purchase_order.action_view_invoice()
            return {'type': 'ir.actions.act_window_close'}
        if self._context.get('open_invoices', False):
            return purchase_order.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}
