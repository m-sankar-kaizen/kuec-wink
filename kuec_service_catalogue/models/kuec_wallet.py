# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class KuecWalletTransaction(models.Model):
    _name = 'kuec.wallet.transaction'
    _description = 'WINK eWallet Transaction'
    _order = 'date desc, id desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='restrict',
        index=True,
        help='The customer whose wallet this transaction belongs to.',
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        required=True,
        help='Date of the transaction.',
    )
    transaction_type = fields.Selection([
        ('topup', 'Top-Up'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
    ], string='Type', required=True, default='topup',
        help='Type of wallet transaction.',
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        help='Positive = credit (funds added). Negative = debit (funds used).',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
        help='Currency used for this transaction.',
    )
    description = fields.Char(
        string='Description',
        required=True,
        help='Short description of this transaction (e.g. "Top-up by coordinator", "Payment for S00051").',
    )
    order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        ondelete='set null',
        help='The service request this payment is linked to (for payment transactions).',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help='Company this transaction belongs to.',
    )
    state = fields.Selection([
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='done', required=True,
        help='Status of the transaction. Cancelled transactions are excluded from the wallet balance.',
    )
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True,
        help='User who created this transaction record.',
    )
