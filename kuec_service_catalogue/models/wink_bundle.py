# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
    product_variant_id = fields.Many2one(
        'product.product',
        string='Mapped Product Variant',
        help="Map this tier to a specific product variant so Odoo's native Recurring Prices can be used.",
        ondelete='restrict',
    )
    name = fields.Char(
        string='Tier Name',
        required=True,
        help="e.g. Starter, Professional, Enterprise",
    )
    description = fields.Text(
        string='Description',
        help="Description of this tier and its specific benefits.",
    )
    sequence = fields.Integer(
        default=10,
    )
    price = fields.Float(
        string='Price (Legacy)',
        digits=(10, 2),
        help="Legacy static price. For retainers, native product variant pricing is used instead.",
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

    _sql_constraints = [
        ('unique_service_per_tier',
         'UNIQUE(tier_id, service_product_id)',
         'Each service can only appear once per tier.'),
    ]

    tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='Tier',
        required=True,
        ondelete='cascade',
        index=True,
    )
    service_product_id = fields.Many2one(
        'product.template',
        string='Service Application',
        required=True,
        ondelete='restrict',
        domain=[('type', '=', 'service'), ('commercial_structure', 'in', ['bundled', 'flexible'])],
        help="Select a service to include in this tier. Each service can only appear once per tier.",
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

    @api.constrains('tier_id', 'service_product_id')
    def _check_unique_service_per_tier(self):
        for rec in self:
            duplicates = self.search_count([
                ('tier_id', '=', rec.tier_id.id),
                ('service_product_id', '=', rec.service_product_id.id),
                ('id', '!=', rec.id),
            ])
            if duplicates:
                raise ValidationError(
                    _('The service "%s" is already included in tier "%s". '
                      'Each service can only appear once per tier.')
                    % (rec.service_product_id.name, rec.tier_id.name)
                )
