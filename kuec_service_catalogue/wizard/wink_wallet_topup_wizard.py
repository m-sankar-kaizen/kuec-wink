# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _
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
        domain=[('type', 'in', ['bank', 'cash']), ('is_ewallet_journal', '=', False)],
        help='Journal representing the payment source (Bank, Cash, Payment Gateway, etc.). The eWallet journal is excluded.',
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
            2. Locate the WINK eWallet journal (WEWL).
            3. Resolve the source account (bank/cash journal liquidity account) and the
               WEWL liability account (WEWL journal default account).
            4. Post a direct account.move on the WEWL journal:
               DR  Bank/Cash liquidity account  (money received)
               CR  WEWL liability account       (wallet balance increases)
            5. Create a kuec.wallet.transaction linked to the journal entry.

        Note:
            In Odoo 18, account.payment no longer carries destination_journal_id for
            internal transfers.  A direct account.move gives us full control over
            which accounts are debited/credited without involving AR/AP.

        Returns:
            dict: Action to close the wizard dialog.
        """
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_('Top-up amount must be positive.'))

        wallet_journal = self.env['account.journal'].search(
            [('is_ewallet_journal', '=', True), ('company_id', '=', self.env.company.id)], limit=1
        )
        if not wallet_journal:
            raise UserError(_(
                'No eWallet journal is configured. '
                'Please go to Accounting → Configuration → Journals, '
                'open the eWallet journal and enable "eWallet Journal".'
            ))

        if self.journal_id.id == wallet_journal.id:
            raise UserError(_('Payment journal and eWallet journal cannot be the same.'))

        # Source: bank/cash journal liquidity account
        source_account = self.journal_id.default_account_id
        if not source_account:
            raise UserError(_(
                'The selected journal "%s" has no default account configured.'
            ) % self.journal_id.name)

        # Destination: eWallet journal liability account
        wewl_account = wallet_journal.default_account_id
        if not wewl_account:
            raise UserError(_(
                'The eWallet journal has no default account configured. '
                'Please set it in Accounting > Configuration > Journals.'
            ))

        memo = self.description or 'Wallet Top-Up'

        # Post direct journal entry: DR bank account / CR WEWL liability
        move = self.env['account.move'].create({
            'journal_id': wallet_journal.id,
            'ref': memo,
            'line_ids': [
                Command.create({
                    'account_id': source_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'name': memo,
                    'currency_id': self.currency_id.id,
                }),
                Command.create({
                    'account_id': wewl_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'name': memo,
                    'currency_id': self.currency_id.id,
                }),
            ],
        })
        move.action_post()

        # Create wallet transaction record linked to the journal entry
        self.env['kuec.wallet.transaction'].create({
            'partner_id': self.partner_id.id,
            'transaction_type': 'topup',
            'amount': self.amount,
            'description': memo,
            'currency_id': self.currency_id.id,
            'move_id': move.id,
        })
        return {'type': 'ir.actions.act_window_close'}
