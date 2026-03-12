# -*- coding: utf-8 -*-
# Bundle Lifecycle: upgrade, downgrade, cancellation audit trail

from odoo import models, fields


class WinkBundleChangeLog(models.Model):
    _name = 'wink.bundle.change.log'
    _description = 'WINK Bundle Change Log'
    _order = 'date desc, id desc'

    order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
        index=True,
        help='The bundle sale order this change belongs to.',
    )
    change_type = fields.Selection(
        [('upgrade', 'Upgrade'), ('downgrade', 'Downgrade'), ('cancel', 'Cancellation')],
        string='Change Type',
        required=True,
        help='Type of lifecycle change: upgrade, downgrade, or cancellation.',
    )
    from_tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='Previous Tier',
        ondelete='set null',
        help='The bundle tier before the change (null for first activation).',
    )
    to_tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='New Tier',
        ondelete='set null',
        help='The bundle tier after the change (null for cancellation).',
    )
    refund_amount = fields.Monetary(
        string='Refund / Credit Amount',
        currency_field='currency_id',
        help='Amount refunded or credited to the customer (pro-rata calculation).',
    )
    charge_amount = fields.Monetary(
        string='Charge Amount',
        currency_field='currency_id',
        help='Additional amount charged to the customer (e.g. upgrade pro-rata charge).',
    )
    currency_id = fields.Many2one(
        related='order_id.currency_id',
        string='Currency',
        readonly=True,
    )
    credit_note_id = fields.Many2one(
        'account.move',
        string='Credit Note',
        ondelete='set null',
        help='Credit note created for this change (refund or credit).',
    )
    charge_line_id = fields.Many2one(
        'sale.order.line',
        string='Charge Order Line',
        ondelete='set null',
        help='SO line created for the upgrade pro-rata charge.',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Initiated By',
        default=lambda self: self.env.user.id,
        ondelete='set null',
        help='User who triggered this lifecycle change (portal or internal).',
    )
    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        required=True,
        help='Timestamp of the lifecycle event.',
    )
    state = fields.Selection(
        [('done', 'Done'), ('failed', 'Failed')],
        string='State',
        default='done',
        help='Whether the change was completed successfully or failed.',
    )
    note = fields.Text(
        string='Note',
        help='Reason provided by the customer or internal note about this change.',
    )
    remaining_days = fields.Integer(
        string='Remaining Days',
        help='Number of days remaining in the billing period at the time of the change.',
    )
    total_days = fields.Integer(
        string='Total Period Days',
        help='Total days in the billing period.',
    )
