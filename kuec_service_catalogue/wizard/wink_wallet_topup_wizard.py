# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError


class WinkWalletTopupWizard(models.TransientModel):
    _name = 'wink.wallet.topup.wizard'
    _description = 'WINK eWallet Top-Up Wizard'

    topup_type = fields.Selection([
        ('payment', 'Customer Payment'),
        ('gift', 'Gift / Expense'),
    ], string='Top-Up Type', required=True, default='payment',
        help='Customer Payment: customer paid via bank/cash — DR bank account, CR WEWL liability.\n'
             'Gift / Expense: company-funded gift — DR expense account, CR WEWL liability. '
             'No bank or cash movement is recorded.',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        help='Customer whose wallet to top up.',
    )
    # ── Payment top-up fields ─────────────────────────────────────────────────
    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        domain=[('type', 'in', ['bank', 'cash']), ('is_ewallet_journal', '=', False)],
        help='Journal representing the payment source (Bank, Cash, Payment Gateway, etc.).',
    )
    # ── Gift / Expense top-up fields ──────────────────────────────────────────
    expense_account_id = fields.Many2one(
        'account.account',
        string='Expense Account',
        domain=[('account_type', 'like', 'expense')],
        help='Expense account to debit for this gift (e.g. "Customer Gifts & Donations", "Marketing Expense").',
    )
    gift_journal_id = fields.Many2one(
        'account.journal',
        string='Expense Journal',
        domain=[('type', '=', 'general')],
        default=lambda self: self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.env.company.id)], limit=1
        ),
        help='General/miscellaneous journal for posting the gift expense entry.',
    )
    gift_reason = fields.Char(
        string='Gift Reason',
        help='Internal note explaining why this gift was granted (e.g. "Ramadan gift", "Loyalty reward").',
    )
    # ── Common fields ─────────────────────────────────────────────────────────
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
        string='Description / Memo',
        help='Optional note that appears on the journal entry.',
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

    def _get_wallet_journal_and_account(self):
        """Return (wallet_journal, wewl_account) or raise UserError if not configured."""
        wallet_journal = self.env['account.journal'].search(
            [('is_ewallet_journal', '=', True), ('company_id', '=', self.env.company.id)], limit=1
        )
        if not wallet_journal:
            raise UserError(_(
                'No eWallet journal is configured. '
                'Please go to Accounting → Configuration → Journals, '
                'open the eWallet journal and enable "eWallet Journal".'
            ))
        wewl_account = wallet_journal.default_account_id
        if not wewl_account:
            raise UserError(_(
                'The eWallet journal has no default account configured. '
                'Please set it in Accounting → Configuration → Journals.'
            ))
        return wallet_journal, wewl_account

    def action_topup(self):
        """Create a wallet transaction and post the corresponding journal entry.

        Workflow:
            1. Validate inputs based on topup_type.
            2. Locate the WINK eWallet journal (WEWL) and its liability account.
            3. For 'payment': post JV on bank/cash journal — DR bank, CR WEWL.
            4. For 'gift':    post JV on general journal  — DR expense, CR WEWL.
            5. Create a kuec.wallet.transaction linked to the journal entry.

        Returns:
            dict: Action to close the wizard dialog.
        """
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_('Top-up amount must be positive.'))

        wallet_journal, wewl_account = self._get_wallet_journal_and_account()

        if self.topup_type == 'payment':
            self._action_topup_payment(wallet_journal, wewl_account)
        else:
            self._action_topup_gift(wewl_account)

        return {'type': 'ir.actions.act_window_close'}

    def _action_topup_payment(self, wallet_journal, wewl_account):
        """Post a customer-payment top-up JV: DR bank/cash, CR WEWL.

        Workflow:
            1. Validate journal selection and source account availability.
            2. Create and post account.move on the bank/cash journal.
            3. Create kuec.wallet.transaction of type 'topup'.
        """
        if not self.journal_id:
            raise UserError(_('Please select a payment journal.'))
        if self.journal_id.id == wallet_journal.id:
            raise UserError(_('Payment journal and eWallet journal cannot be the same.'))

        source_account = self.journal_id.default_account_id
        if not source_account:
            raise UserError(_(
                'The selected journal "%s" has no default account configured.'
            ) % self.journal_id.name)

        memo = self.description or _('Wallet Top-Up — %s') % self.partner_id.name

        move = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
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

        self.env['kuec.wallet.transaction'].create({
            'partner_id': self.partner_id.id,
            'transaction_type': 'topup',
            'amount': self.amount,
            'description': memo,
            'currency_id': self.currency_id.id,
            'move_id': move.id,
        })

    def _action_topup_gift(self, wewl_account):
        """Post a gift/expense top-up JV: DR expense account, CR WEWL.

        Workflow:
            1. Validate expense account, journal, and reason.
            2. Create and post account.move on the general expense journal.
            3. Create kuec.wallet.transaction of type 'adjustment' with gift prefix.
        """
        if not self.expense_account_id:
            raise UserError(_('Please select an expense account for the gift top-up.'))
        if not self.gift_journal_id:
            raise UserError(_('Please select an expense journal for the gift entry.'))
        if not self.gift_reason:
            raise UserError(_('Please provide a reason for this gift (e.g. "Ramadan gift").'))

        reason = self.gift_reason.strip()
        memo = _('Gift: %(reason)s — %(partner)s') % {
            'reason': reason,
            'partner': self.partner_id.name,
        }
        if self.description:
            memo = self.description

        move = self.env['account.move'].create({
            'journal_id': self.gift_journal_id.id,
            'ref': memo,
            'line_ids': [
                Command.create({
                    'account_id': self.expense_account_id.id,
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

        self.env['kuec.wallet.transaction'].create({
            'partner_id': self.partner_id.id,
            'transaction_type': 'adjustment',
            'amount': self.amount,
            'description': memo,
            'currency_id': self.currency_id.id,
            'move_id': move.id,
        })
