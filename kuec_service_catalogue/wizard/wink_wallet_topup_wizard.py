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
    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        required=True,
        domain=[('type', 'in', ['bank', 'cash'])],
        help='Journal representing the payment source (Bank, Cash, Payment Gateway, etc.).',
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
        default='Wallet Top-Up',
        help='Optional note about this top-up (appears on the journal entry memo).',
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
        """Create a wallet transaction and post the corresponding journal entry.

        Workflow:
            1. Validate the amount is positive.
            2. Locate the WINK eWallet journal (WEWL) as the destination.
            3. Create an inbound account.payment:
               DR  Selected payment journal (Bank/Gateway)
               CR  WINK eWallet journal (Customer Wallet Liability)
            4. Post the payment to generate the journal entry.
            5. Create a kuec.wallet.transaction linked to the journal entry.

        Returns:
            dict: Action to close the wizard dialog.
        """
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_('Top-up amount must be positive.'))

        wallet_journal = self.env['account.journal'].search(
            [('code', '=', 'WEWL'), ('company_id', '=', self.env.company.id)], limit=1
        )
        if not wallet_journal:
            raise UserError(_(
                'WINK eWallet journal (code: WEWL) not found. '
                'Please check your accounting configuration.'
            ))

        if self.journal_id.id == wallet_journal.id:
            raise UserError(_('Payment journal and eWallet journal cannot be the same.'))

        # Create inbound payment: Bank/Gateway → WEWL (internal transfer)
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'journal_id': self.journal_id.id,
            'destination_journal_id': wallet_journal.id,
            'ref': self.description or 'Wallet Top-Up',
            'company_id': self.env.company.id,
        })
        payment.action_post()

        # Create wallet transaction record linked to the generated journal entry
        move = payment.move_id
        self.env['kuec.wallet.transaction'].create({
            'partner_id': self.partner_id.id,
            'transaction_type': 'topup',
            'amount': self.amount,
            'description': self.description or 'Wallet Top-Up',
            'currency_id': self.currency_id.id,
            'move_id': move.id if move else False,
        })
        return {'type': 'ir.actions.act_window_close'}
