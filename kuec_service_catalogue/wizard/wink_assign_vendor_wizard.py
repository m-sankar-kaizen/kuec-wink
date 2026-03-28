# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WinkAssignVendorWizard(models.TransientModel):
    _name = 'wink.assign.vendor.wizard'
    _description = 'Assign Vendor & Create RFQ'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        help='The delivery task this vendor will be assigned to.',
    )
    order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        help='The quotation this vendor is being pre-assigned to (used when no task exists yet).',
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain=[('is_company', '=', True)],
        help='Select the vendor to deliver this service. A draft RFQ will be created automatically.',
    )

    def action_assign(self):
        """Assign the vendor and create a draft RFQ.

        Workflow:
            1. If task_id is set: delegate to existing task-level logic.
            2. If order_id is set (no task): store vendor on order, create RFQ
               from the source product, store PO ref on order, post chatter note.
        """
        self.ensure_one()
        if self.task_id:
            return self._action_assign_task()
        if self.order_id:
            return self._action_assign_order()
        raise UserError(_('No task or order linked to this wizard.'))

    def _action_assign_task(self):
        """Existing task-level vendor assignment."""
        task = self.task_id
        if not task.exists():
            raise UserError(_('The linked task no longer exists.'))
        task.wink_vendor_id = self.vendor_id
        task.action_assign_vendor_rfq()
        return {'type': 'ir.actions.act_window_close'}

    def _action_assign_order(self):
        """Order-level vendor assignment — no task exists yet.

        Creates a draft RFQ against the source service product and stores
        the PO reference on the order. On confirmation, the PO is linked
        to the auto-created task instead of creating a duplicate.
        """
        order = self.order_id
        if not order.exists():
            raise UserError(_('The linked order no longer exists.'))

        order.wink_vendor_id = self.vendor_id

        product = None
        if order.wink_source_product_id:
            product = order.wink_source_product_id.product_variant_ids[:1]
        elif order.order_line:
            product = order.order_line[0].product_id

        po_line_vals = []
        if product:
            po_line_vals.append((0, 0, {
                'product_id': product.id,
                'name': product.display_name,
                'product_qty': 1.0,
                'price_unit': 0.0,
                'date_planned': fields.Datetime.now(),
            }))

        po = self.env['purchase.order'].sudo().create({
            'partner_id': self.vendor_id.id,
            'origin': order.name,
            'notes': _('Pre-assigned from WINK quotation: %s') % order.name,
            'order_line': po_line_vals,
        })
        order.sudo().write({'wink_preassigned_po_id': po.id})

        order.message_post(
            body=_(
                'Vendor %(vendor)s pre-assigned. RFQ %(po)s created.',
                vendor=self.vendor_id.name,
                po=po.name,
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
        }
