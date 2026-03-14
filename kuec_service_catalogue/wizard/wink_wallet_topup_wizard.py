# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WinkWalletTopupWizard(models.TransientModel):
    _name = 'wink.wallet.topup.wizard'
    _description = 'WINK eWallet Top-Up Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        help='Customer whose wallet to top up.',
    )
    amount = fields.Monetary(
        string='Top-Up Amount',
        required=True,
        currency_field='currency_id',
        help='Amount to add to the customer wallet (must be positive).',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
        help='Currency for this top-up transaction.',
    )
    description = fields.Char(
        string='Description',
        default='Top-up by coordinator',
        help='Optional note about this top-up.',
    )
    current_balance = fields.Monetary(
        string='Current Balance',
        currency_field='currency_id',
        compute='_compute_current_balance',
        help='Current eWallet balance for the selected customer before this top-up.',
    )

    @api.depends('partner_id')
    def _compute_current_balance(self):
        """Display the partner's current wallet balance in the wizard for reference."""
        for rec in self:
            rec.current_balance = rec.partner_id.wink_wallet_balance if rec.partner_id else 0.0

    def action_topup(self):
        """Validate the top-up amount and create a wallet transaction record.

        Args:
            None — operates on self (singleton wizard).

        Returns:
            dict: Action to close the wizard dialog.
        """
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_('Top-up amount must be positive.'))
        self.env['kuec.wallet.transaction'].create({
            'partner_id': self.partner_id.id,
            'transaction_type': 'topup',
            'amount': self.amount,
            'description': self.description or 'Top-up by coordinator',
            'currency_id': self.currency_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}
