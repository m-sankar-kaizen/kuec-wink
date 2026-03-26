# -*- coding: utf-8 -*-

from odoo import models, fields, _


class WinkFinalizeWizard(models.TransientModel):
    _name = 'wink.finalize.wizard'
    _description = 'Finalize & Unlock Payment Wizard'

    order_id = fields.Many2one(
        'sale.order',
        string='Service Request',
        required=True,
        readonly=True,
        ondelete='cascade',
        help='The portal service request being finalized.',
    )
    service_name = fields.Char(
        related='order_id.wink_source_product_id.name',
        string='Service',
        readonly=True,
    )
    customer_name = fields.Char(
        related='order_id.partner_id.name',
        string='Customer',
        readonly=True,
    )
    amount_total = fields.Monetary(
        related='order_id.amount_total',
        string='Total Amount',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='order_id.currency_id',
        readonly=True,
    )
    coordinator_note = fields.Text(
        string='Note to Customer',
        help='Optional message posted on the request to inform the customer that pricing is ready.',
    )

    def action_finalize(self):
        """Set wink_price_confirmed=True and post a chatter message."""
        self.ensure_one()
        order = self.order_id
        order.wink_price_confirmed = True
        body = _('Pricing has been finalized and payment is now unlocked for the customer.')
        if self.coordinator_note:
            body += '\nNote: ' + self.coordinator_note
        order.message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return {'type': 'ir.actions.act_window_close'}
