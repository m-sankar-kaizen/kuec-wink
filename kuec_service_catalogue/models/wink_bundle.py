# -*- coding: utf-8 -*-
# F-2: Smart Buttons on Bundle Form (order_count, total_services, active_subscriptions)
# B-4: Tier Comparison Matrix (action)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WinkBundle(models.Model):
    _name = 'wink.bundle'
    _description = 'WINK Bundle Package'
    _order = 'name'

    name = fields.Char(
        string='Bundle Name',
        required=True,
        help='Display name for this bundle package (e.g. "Business Setup Package").',
    )
    description = fields.Text(
        string='Description',
        help='Internal notes about this bundle package.',
    )
    active = fields.Boolean(
        default=True,
        help='Archived bundles are hidden from portal and new requests.',
    )
    tier_ids = fields.One2many(
        'wink.bundle.tier',
        'bundle_id',
        string='Tiers',
    )

    # --- Self-service lifecycle policy (one-time admin config) ---
    allow_self_service_upgrade = fields.Boolean(
        string='Allow Self-Service Upgrade',
        default=True,
        help='When enabled, customers can upgrade their tier directly from the portal without coordinator approval.',
    )
    allow_self_service_downgrade = fields.Boolean(
        string='Allow Self-Service Downgrade',
        default=True,
        help='When enabled, customers can downgrade their tier directly from the portal without coordinator approval.',
    )
    allow_self_service_cancel = fields.Boolean(
        string='Allow Self-Service Cancellation',
        default=True,
        help='When enabled, customers can cancel their bundle directly from the portal.',
    )
    cancel_refund_policy = fields.Selection(
        [
            ('pro_rata', 'Pro-Rata (annual price)'),
            ('monthly_rate', 'Monthly Rate (yearly discount forfeited)'),
            ('none', 'No Refund'),
        ],
        string='Cancellation Refund Policy',
        default='monthly_rate',
        help='How the refund is calculated when a customer cancels.\n'
             '• Pro-Rata: refunds the proportion of the annual price for remaining days.\n'
             '• Monthly Rate: refunds using the standard monthly price — yearly discount is forfeited.\n'
             '• No Refund: no credit note is created.',
    )
    downgrade_credit_policy = fields.Selection(
        [
            ('pro_rata', 'Pro-Rata Credit'),
            ('none', 'No Credit on Downgrade'),
        ],
        string='Downgrade Credit Policy',
        default='pro_rata',
        help='Whether to issue a pro-rata credit note when the customer downgrades to a cheaper tier.',
    )
    tier_count = fields.Integer(
        compute='_compute_tier_count',
        store=True,
        help='Number of tiers configured for this bundle.',
    )

    # F-2: Smart button computed fields
    order_count = fields.Integer(
        string='Orders',
        compute='_compute_order_count',
        help='Number of sale orders using this bundle.',
    )
    total_services = fields.Integer(
        string='Total Services',
        compute='_compute_total_services',
        help='Total number of unique services across all tiers.',
    )
    active_subscription_count = fields.Integer(
        string='Active Subscriptions',
        compute='_compute_active_subscription_count',
        help='Number of confirmed or ongoing orders using this bundle.',
    )

    @api.depends('tier_ids')
    def _compute_tier_count(self):
        for rec in self:
            rec.tier_count = len(rec.tier_ids)

    # F-2: Compute order count for smart button
    @api.depends('tier_ids', 'tier_ids.item_ids')
    def _compute_order_count(self):
        for rec in self:
            # Find product templates that use this bundle
            products = self.env['product.template'].search([
                ('wink_bundle_id', '=', rec.id),
            ])
            if products:
                count = self.env['sale.order'].search_count([
                    ('wink_source_product_id', 'in', products.ids),
                    ('state', '!=', 'cancel'),
                ])
            else:
                count = 0
            rec.order_count = count

    # F-2: Compute total unique services
    @api.depends('tier_ids', 'tier_ids.item_ids', 'tier_ids.item_ids.service_product_id')
    def _compute_total_services(self):
        for rec in self:
            service_ids = set()
            for tier in rec.tier_ids:
                for item in tier.item_ids:
                    service_ids.add(item.service_product_id.id)
            rec.total_services = len(service_ids)

    # F-2: Compute active subscriptions
    @api.depends('tier_ids')
    def _compute_active_subscription_count(self):
        for rec in self:
            products = self.env['product.template'].search([
                ('wink_bundle_id', '=', rec.id),
            ])
            if products:
                count = self.env['sale.order'].search_count([
                    ('wink_source_product_id', 'in', products.ids),
                    ('state', 'in', ['sale', 'done']),
                ])
            else:
                count = 0
            rec.active_subscription_count = count

    # F-2: Smart button actions
    def action_view_orders(self):
        """Open orders using this bundle."""
        self.ensure_one()
        products = self.env['product.template'].search([
            ('wink_bundle_id', '=', self.id),
        ])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bundle Orders'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('wink_source_product_id', 'in', products.ids),
                ('state', '!=', 'cancel'),
            ],
            'context': {'default_wink_is_portal_request': True},
        }

    def action_view_active_subscriptions(self):
        """Open active subscriptions using this bundle."""
        self.ensure_one()
        products = self.env['product.template'].search([
            ('wink_bundle_id', '=', self.id),
        ])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Active Subscriptions'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('wink_source_product_id', 'in', products.ids),
                ('state', 'in', ['sale', 'done']),
            ],
        }

    # B-4: Tier Comparison Matrix action
    def action_view_tier_comparison(self):
        """Open a pivot-like comparison of all tiers and their services."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tier Comparison — %s') % self.name,
            'res_model': 'wink.bundle.tier.item',
            'view_mode': 'list',
            'domain': [('tier_id', 'in', self.tier_ids.ids)],
            'context': {
                'group_by': ['tier_id'],
                'search_default_group_by_tier': 1,
            },
        }


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
        help='Parent bundle package this tier belongs to.',
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
        help='Lower sequence = displayed first. Drag handle for reordering.',
    )
    price = fields.Float(
        string='Price (Legacy)',
        digits=(10, 2),
        help="Legacy static price. For retainers, native product variant pricing is used instead.",
    )
    # U-4: Most Popular flag for portal display
    is_most_popular = fields.Boolean(
        string='Most Popular',
        default=False,
        help='Flag this tier as "Most Popular" — shown with a badge on the portal configurator.',
    )
    item_ids = fields.One2many(
        'wink.bundle.tier.item',
        'tier_id',
        string='Included Services',
    )
    item_count = fields.Integer(
        compute='_compute_item_count',
        store=True,
        help='Number of services included in this tier.',
    )

    # --- Lifecycle: upgrade / downgrade targets (one-time admin config) ---
    upgrade_to_ids = fields.Many2many(
        'wink.bundle.tier',
        'wink_tier_upgrade_rel',
        'from_tier_id',
        'to_tier_id',
        string='Can Upgrade To',
        domain="[('bundle_id', '=', bundle_id), ('id', '!=', id)]",
        help='Tiers a customer on this tier may self-service upgrade to.',
    )
    downgrade_to_ids = fields.Many2many(
        'wink.bundle.tier',
        'wink_tier_downgrade_rel',
        'from_tier_id',
        'to_tier_id',
        string='Can Downgrade To',
        domain="[('bundle_id', '=', bundle_id), ('id', '!=', id)]",
        help='Tiers a customer on this tier may self-service downgrade to.',
    )
    price_monthly = fields.Float(
        string='Monthly Price (Std)',
        digits=(10, 2),
        help='Standard monthly price used for refund/credit calculations when yearly discount is forfeited on cancellation or downgrade.',
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

    def action_open_add_services_wizard(self):
        """Open the multi-select Add Services wizard pre-filled with this tier."""
        self.ensure_one()
        wizard = self.env['wink.add.services.wizard'].create({'tier_id': self.id})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Services — %s') % self.name,
            'res_model': 'wink.add.services.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
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
        help='Parent tier this service item belongs to.',
    )
    # B-4: Related field for grouping in comparison matrix
    bundle_id = fields.Many2one(
        related='tier_id.bundle_id',
        string='Bundle',
        store=True,
        readonly=True,
        help='Bundle package (from parent tier, for search/group-by).',
    )
    tier_name = fields.Char(
        related='tier_id.name',
        string='Tier Name',
        store=True,
        readonly=True,
        help='Tier name (from parent tier, for comparison matrix).',
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
        help='Order of services in the tier listing. Use drag handle for reordering.',
    )
    description = fields.Char(
        string='Description',
        help='Custom description for this service when displayed in this tier.',
    )
    qty = fields.Integer(
        string='Quantity',
        default=1,
        required=True,
        help="Number of times this service is included in the bundle tier.",
    )

    @api.onchange('service_product_id')
    def _onchange_service_product_id_duplicate(self):
        """Warn and clear immediately if the selected service is already in this tier.

        Fires before save so the user gets instant feedback instead of a cryptic
        DB constraint error after clicking Save.
        """
        if not self.service_product_id or not self.tier_id:
            return
        already_used = self.tier_id.item_ids.filtered(
            lambda x: x.service_product_id == self.service_product_id and x != self._origin
        )
        if already_used:
            self.service_product_id = False
            return {
                'warning': {
                    'title': _('Duplicate Service'),
                    'message': _(
                        '"%s" is already included in tier "%s". '
                        'Each service can only appear once per tier.'
                    ) % (already_used[0].service_product_id.name, self.tier_id.name),
                }
            }

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
