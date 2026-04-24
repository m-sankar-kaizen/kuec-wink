# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError


class WinkWalletTopupWizard(models.TransientModel):
    _name = 'wink.wallet.topup.wizard'
    _description = 'WINK eWallet Top-Up Wizard'

    topup_type = fields.Selection([
        ('payment', 'Prepaid Credit'),
        ('gift', 'Promotional Credit'),
    ], string='Top-Up Type', required=True, default='payment',
        help='Prepaid Credit: customer paid via bank/cash — DR bank account, CR WEWL liability.\n'
             'Promotional Credit: company-funded credit — DR expense account, CR WEWL liability. '
             'No bank or cash movement is recorded.\n'
             'Prepaid Credit allows negative amounts (overdraft): DR WEWL, CR bank.',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        help='Customer whose wallet to top up.',
    )
    # ── Prepaid Credit fields ─────────────────────────────────────────────────
    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        domain=[('type', 'in', ['bank', 'cash']), ('is_ewallet_journal', '=', False)],
        help='Journal representing the payment source (Bank, Cash, Payment Gateway, etc.).',
    )
    # ── Promotional Credit fields ─────────────────────────────────────────────
    expense_account_id = fields.Many2one(
        'account.account',
        string='Expense Account',
        domain=[('account_type', 'like', 'expense')],
        help='Expense account to debit for this promotional credit (e.g. "Customer Gifts & Donations").',
    )
    gift_journal_id = fields.Many2one(
        'account.journal',
        string='Expense Journal',
        domain=[('type', '=', 'general')],
        default=lambda self: self.env.company.wink_expense_journal_id
            or self.env['account.journal'].search(
                [('type', '=', 'general'), ('company_id', '=', self.env.company.id)], limit=1
            ),
        help='General/miscellaneous journal for posting the promotional credit expense entry. '
             'Default is set in Settings → WINK → eWallet.',
    )
    # ── Common fields ─────────────────────────────────────────────────────────
    amount = fields.Monetary(
        string='Top-Up Amount',
        required=True,
        currency_field='currency_id',
        help='Amount to add to the customer wallet. '
             'For Prepaid Credit, negative values are allowed (overdraft: DR wallet, CR cash/bank).',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
        help='Currency for this top-up transaction.',
    )
    description = fields.Char(
        string='Description / Reason',
        help='Memo shown on the journal entry. For Promotional Credit, also used as the reason.',
    )
    current_balance = fields.Monetary(
        string='Current Balance',
        currency_field='currency_id',
        compute='_compute_current_balance',
        help='Current eWallet balance for the selected customer before this top-up.',
    )

    @api.depends('partner_id')
    def _compute_current_balance(self):
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
            3. For 'payment': post JV on bank/cash journal.
               Positive: DR bank, CR WEWL. Negative (overdraft): DR WEWL, CR bank.
            4. For 'gift':    post JV on general journal — DR expense, CR WEWL.
            5. Create a kuec.wallet.transaction linked to the journal entry.

        Returns:
            dict: Action to close the wizard dialog.
        """
        self.ensure_one()
        if self.amount == 0:
            raise UserError(_('Amount cannot be zero.'))
        if self.topup_type == 'gift' and self.amount < 0:
            raise UserError(_('Promotional Credit amount must be positive.'))

        wallet_journal, wewl_account = self._get_wallet_journal_and_account()

        if self.topup_type == 'payment':
            self._action_topup_payment(wallet_journal, wewl_account)
        else:
            self._action_topup_gift(wewl_account)

        return {'type': 'ir.actions.act_window_close'}

    def _action_topup_payment(self, wallet_journal, wewl_account):
        """Post a prepaid credit top-up JV.

        Positive amount (normal): DR bank/cash, CR WEWL.
        Negative amount (overdraft): DR WEWL, CR bank/cash.

        Workflow:
            1. Validate journal selection and source account availability.
            2. Build debit/credit amounts — flip sides for negative (overdraft).
            3. Create and post account.move on the bank/cash journal.
            4. Create kuec.wallet.transaction of type 'topup' (signed amount).
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

        memo = self.description or (
            _('Wallet Overdraft — %s') % self.partner_id.name
            if self.amount < 0
            else _('Wallet Top-Up — %s') % self.partner_id.name
        )

        amt = abs(self.amount)
        if self.amount > 0:
            # Normal top-up: DR bank/cash, CR WEWL
            source_debit, source_credit = amt, 0.0
            wewl_debit, wewl_credit = 0.0, amt
        else:
            # Overdraft: DR WEWL, CR bank/cash
            source_debit, source_credit = 0.0, amt
            wewl_debit, wewl_credit = amt, 0.0

        move = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'ref': memo,
            'line_ids': [
                Command.create({
                    'account_id': source_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': source_debit,
                    'credit': source_credit,
                    'name': memo,
                    'currency_id': self.currency_id.id,
                }),
                Command.create({
                    'account_id': wewl_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': wewl_debit,
                    'credit': wewl_credit,
                    'name': memo,
                    'currency_id': self.currency_id.id,
                }),
            ],
        })
        move.action_post()

        self.env['kuec.wallet.transaction'].create({
            'partner_id': self.partner_id.id,
            'transaction_type': 'topup',
            'amount': self.amount,  # signed: negative for overdraft
            'description': memo,
            'currency_id': self.currency_id.id,
            'move_id': move.id,
        })

    def _action_topup_gift(self, wewl_account):
        """Post a promotional credit top-up JV: DR expense account, CR WEWL.

        Workflow:
            1. Validate expense account, journal, and description/reason.
            2. Create and post account.move on the general expense journal.
            3. Create kuec.wallet.transaction of type 'adjustment'.
        """
        if not self.expense_account_id:
            raise UserError(_('Please select an expense account for the promotional credit.'))
        if not self.gift_journal_id:
            raise UserError(_(
                'Please select an expense journal. '
                'You can set a default in Settings → WINK → eWallet.'
            ))
        if not self.description:
            raise UserError(_('Please provide a description/reason for this promotional credit.'))

        memo = _('Promotional Credit: %(reason)s — %(partner)s') % {
            'reason': self.description.strip(),
            'partner': self.partner_id.name,
        }

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
