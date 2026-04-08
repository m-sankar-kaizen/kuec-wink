# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError


class WinkWalletPaymentWizard(models.TransientModel):
    _name = 'wink.wallet.payment.wizard'
    _description = 'WINK eWallet Payment Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        help='Customer whose wallet balance will be used to pay the invoice.',
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        domain="[('move_type','=','out_invoice'), ('state','=','posted'), "
               "('payment_state','in',['not_paid','partial']), ('partner_id','=',partner_id)]",
        help='Posted customer invoice to settle using the eWallet balance.',
    )
    amount = fields.Monetary(
        string='Payment Amount',
        required=True,
        currency_field='currency_id',
        help='Amount to pay from the wallet. Cannot exceed wallet balance or invoice amount due.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
        help='Currency of the payment.',
    )
    wallet_balance = fields.Monetary(
        string='Wallet Balance',
        currency_field='currency_id',
        compute='_compute_wallet_balance',
        help='Current eWallet balance available for the selected customer.',
    )
    amount_residual = fields.Monetary(
        string='Amount Due on Invoice',
        currency_field='currency_id',
        compute='_compute_amount_residual',
        help='Remaining unpaid amount on the selected invoice.',
    )
    description = fields.Char(
        string='Memo',
        help='Optional note for the journal entry (defaults to invoice reference).',
    )

    @api.depends('partner_id')
    def _compute_wallet_balance(self):
        """Show current wallet balance for the selected customer."""
        for rec in self:
            rec.wallet_balance = rec.partner_id.wink_wallet_balance if rec.partner_id else 0.0

    @api.depends('invoice_id')
    def _compute_amount_residual(self):
        """Show remaining amount due on the selected invoice."""
        for rec in self:
            rec.amount_residual = rec.invoice_id.amount_residual if rec.invoice_id else 0.0

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """Pre-fill amount and memo from the selected invoice."""
        if self.invoice_id:
            self.amount = min(
                self.invoice_id.amount_residual,
                self.wallet_balance,
            )
            self.description = self.invoice_id.name or ''

    def action_pay(self):
        """Settle an invoice using the customer eWallet balance via a direct JV + reconcile.

        Workflow:
            1. Validate amount against wallet balance and invoice residual.
            2. Locate the WINK eWallet journal (WEWL) and its liability account.
            3. Find the exact AR line on the invoice to reconcile against.
            4. Post a direct account.move on the WEWL journal:
               DR  WEWL liability account   (wallet balance decreases)
               CR  AR account from invoice  (same account — guaranteed match)
            5. Manually reconcile the CR AR line with the invoice DR AR line.
               This eliminates the orphaned receivable caused by account.payment.register.
            6. Create kuec.wallet.transaction (payment type, negative amount)
               linked to the generated journal entry.

        Returns:
            dict: Action to close the wizard dialog.
        """
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_('Payment amount must be positive.'))
        if self.amount > self.wallet_balance:
            raise UserError(_(
                'Insufficient wallet balance. '
                'Available: %(balance)s, Requested: %(amount)s',
            ) % {'balance': self.wallet_balance, 'amount': self.amount})
        if self.amount > self.invoice_id.amount_residual:
            raise UserError(_(
                'Payment amount exceeds the invoice amount due (%(due)s).'
            ) % {'due': self.invoice_id.amount_residual})

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
                'Please set it in Accounting > Configuration > Journals.'
            ))

        # Find the AR line on the invoice to reconcile against.
        # This guarantees the CR account matches exactly — no orphaned receivable.
        invoice_ar_line = self.invoice_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
        )
        if not invoice_ar_line:
            raise UserError(_(
                'No open receivable line found on invoice %s. '
                'It may already be fully paid.'
            ) % self.invoice_id.name)
        invoice_ar_line = invoice_ar_line[0]
        ar_account = invoice_ar_line.account_id

        memo = self.description or ('Wallet payment — %s' % self.invoice_id.name)

        # Post direct JV on WEWL journal:
        #   DR  WEWL liability account  (wallet balance decreases)
        #   CR  AR account (same as invoice)  (will be reconciled below)
        move = self.env['account.move'].create({
            'journal_id': wallet_journal.id,
            'ref': memo,
            'line_ids': [
                Command.create({
                    'account_id': wewl_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'name': memo,
                    'currency_id': self.currency_id.id,
                }),
                Command.create({
                    'account_id': ar_account.id,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'name': memo,
                    'currency_id': self.currency_id.id,
                }),
            ],
        })
        move.action_post()

        # Reconcile the CR AR line on the new move with the DR AR line on the invoice.
        payment_ar_line = move.line_ids.filtered(
            lambda l: l.account_id == ar_account
        )
        if payment_ar_line and invoice_ar_line:
            (payment_ar_line + invoice_ar_line).reconcile()

        # Record the debit transaction (negative = funds consumed from wallet)
        self.env['kuec.wallet.transaction'].create({
            'partner_id': self.partner_id.id,
            'transaction_type': 'payment',
            'amount': -self.amount,
            'description': memo,
            'currency_id': self.currency_id.id,
            'order_id': self.invoice_id.invoice_origin and
                        self.env['sale.order'].search(
                            [('name', '=', self.invoice_id.invoice_origin)], limit=1
                        ).id or False,
            'move_id': move.id,
        })
        return {'type': 'ir.actions.act_window_close'}
