# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class WinkBundleEntitlement(models.Model):
    _name = 'wink.bundle.entitlement'
    _description = 'WINK Bundle Entitlement'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='Bundle Tier',
        ondelete='set null',
    )
    service_product_id = fields.Many2one(
        'product.template',
        string='Service',
        required=True,
        ondelete='restrict',
    )
    name = fields.Char(
        string='Description',
        required=True,
    )
    sequence = fields.Integer(
        default=10,
    )
    qty_entitled = fields.Integer(
        string='Entitled Qty',
        default=1,
        help='How many times the customer can activate this service.',
    )
    qty_activated = fields.Integer(
        string='Activated Qty',
        default=0,
        readonly=True,
    )
    state = fields.Selection(
        [
            ('available', 'Available'),
            ('fully_activated', 'Fully Activated'),
        ],
        string='Status',
        compute='_compute_state',
        store=True,
    )
    activated_line_ids = fields.One2many(
        'sale.order.line',
        'wink_entitlement_id',
        string='Activated Order Lines',
        readonly=True,
    )

    @api.depends('qty_entitled', 'qty_activated')
    def _compute_state(self):
        for rec in self:
            if rec.qty_activated >= rec.qty_entitled:
                rec.state = 'fully_activated'
            else:
                rec.state = 'available'

    def action_activate(self):
        """
        Customer or coordinator activates one unit of this
        entitlement. Creates a real sale.order.line on the
        confirmed SO, which triggers Odoo's native sale_project
        to create the Project/Task automatically.
        """
        self.ensure_one()
        if self.qty_activated >= self.qty_entitled:
            raise UserError(_(
                "This service has already been fully activated."
            ))

        order = self.order_id
        if order.state not in ('sale', 'done'):
            raise UserError(_(
                "The order must be confirmed before activating "
                "bundle services."
            ))

        # Get the product variant
        variant = self.service_product_id.product_variant_ids[:1]
        if not variant:
            raise UserError(_(
                "No product variant found for '%(name)s'."
            ) % {'name': self.service_product_id.name})

        # Create a real SO line — Odoo natively creates
        # Project/Task because the SO is already confirmed
        new_line = self.env['sale.order.line'].sudo().create({
            'order_id': order.id,
            'product_id': variant.id,
            'product_uom_qty': 1,
            'price_unit': 0.0,
            'name': self.name,
            'wink_entitlement_id': self.id,
        })

        self.sudo().write({
            'qty_activated': self.qty_activated + 1,
        })

        order.message_post(
            body=(
                f"Bundle service <strong>{self.name}</strong> "
                f"activated ({self.qty_activated}/{self.qty_entitled}). "
                f"Order line #{new_line.id} created."
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        return new_line
