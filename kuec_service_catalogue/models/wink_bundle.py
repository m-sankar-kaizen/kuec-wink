# -*- coding: utf-8 -*-

from odoo import models, fields, api


class WinkBundle(models.Model):
    _name = 'wink.bundle'
    _description = 'WINK Bundle Package'
    _order = 'name'

    name = fields.Char(
        string='Bundle Name',
        required=True,
    )
    description = fields.Text(
        string='Description',
    )
    active = fields.Boolean(
        default=True,
    )
    tier_ids = fields.One2many(
        'wink.bundle.tier',
        'bundle_id',
        string='Tiers',
    )
    tier_count = fields.Integer(
        compute='_compute_tier_count',
        store=True,
    )

    @api.depends('tier_ids')
    def _compute_tier_count(self):
        for rec in self:
            rec.tier_count = len(rec.tier_ids)


class WinkBundleTier(models.Model):
    _name = 'wink.bundle.tier'
    _description = 'WINK Bundle Tier'
    _order = 'sequence, id'

    bundle_id = fields.Many2one(
        'wink.bundle',
        string='Bundle',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(
        string='Tier Name',
        required=True,
        help="e.g. Starter, Professional, Enterprise",
    )
    sequence = fields.Integer(
        default=10,
    )
    price = fields.Float(
        string='Price',
        required=True,
        digits=(10, 2),
    )
    item_ids = fields.One2many(
        'wink.bundle.tier.item',
        'tier_id',
        string='Included Services',
    )
    item_count = fields.Integer(
        compute='_compute_item_count',
        store=True,
    )

    @api.depends('item_ids')
    def _compute_item_count(self):
        for rec in self:
            rec.item_count = len(rec.item_ids)

    def action_open_tier_services(self):
        """Open this tier form so the user can add/edit included services."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wink.bundle.tier',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }


class WinkBundleTierItem(models.Model):
    _name = 'wink.bundle.tier.item'
    _description = 'WINK Bundle Tier Item'
    _order = 'sequence, id'

    tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='Tier',
        required=True,
        ondelete='cascade',
        index=True,
    )
    service_product_id = fields.Many2one(
        'product.template',
        string='Service',
        required=True,
        ondelete='restrict',
        domain=[
            ('available_on_wink', '=', True),
            ('commercial_structure', '!=', 'bundled'),
        ],
    )
    sequence = fields.Integer(
        default=10,
    )
    description = fields.Char(
        string='Description',
    )
    qty = fields.Integer(
        string='Quantity',
        default=1,
        required=True,
        help="Number of times this service is included in the bundle tier.",
    )
