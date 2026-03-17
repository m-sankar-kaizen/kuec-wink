# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
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
        """Register wallet payment against the invoice and post the clearing JV.

        Workflow:
            1. Validate amount against wallet balance and invoice residual.
            2. Locate the WINK eWallet journal (WEWL).
            3. Register account.payment from WEWL journal against the invoice:
               DR  Customer Wallet Liability (WEWL)
               CR  Accounts Receivable (partner)
            4. Odoo auto-reconciles CR AR on this payment with DR AR on invoice.
               Net result: DR Wallet Liability / CR Sales Revenue.
            5. Create kuec.wallet.transaction (payment type, negative amount)
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
            [('code', '=', 'WEWL'), ('company_id', '=', self.env.company.id)], limit=1
        )
        if not wallet_journal:
            raise UserError(_(
                'WINK eWallet journal (code: WEWL) not found. '
                'Please check your accounting configuration.'
            ))

        memo = self.description or ('Wallet payment — %s' % self.invoice_id.name)

        # Register payment from WEWL journal against the invoice
        # DR: WEWL (Customer Wallet Liability)   CR: AR (partner)
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=self.invoice_id.ids,
        ).create({
            'journal_id': wallet_journal.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'ref': memo,
            'payment_date': fields.Date.today(),
        })
        action = payment_register.action_create_payments()

        # Find the created payment to link its journal entry
        payment = self.env['account.payment'].search([
            ('partner_id', '=', self.partner_id.id),
            ('journal_id', '=', wallet_journal.id),
            ('amount', '=', self.amount),
            ('state', '=', 'posted'),
        ], order='id desc', limit=1)

        move_id = payment.move_id.id if payment and payment.move_id else False

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
            'move_id': move_id,
        })
        return {'type': 'ir.actions.act_window_close'}
