# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class KuecWalletTransaction(models.Model):
    _name = 'kuec.wallet.transaction'
    _description = 'WINK eWallet Transaction'
    _order = 'date desc, id desc'
    _rec_name = 'description'

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
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        ondelete='set null',
        help='Accounting journal entry generated for this wallet transaction.',
    )

    def action_view_move(self):
        """Open the linked journal entry in a form view."""
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class AccountJournalWallet(models.Model):
    _inherit = 'account.journal'

    is_ewallet_journal = fields.Boolean(
        string='eWallet Journal',
        default=False,
        help='Mark this journal as the WINK eWallet journal. '
             'Only one journal per company should have this flag enabled. '
             'Used for all eWallet top-up and payment journal entries.',
    )

    def write(self, vals):
        res = super().write(vals)
        if 'is_ewallet_journal' in vals and vals['is_ewallet_journal']:
            for journal in self:
                duplicate = self.env['account.journal'].search([
                    ('is_ewallet_journal', '=', True),
                    ('company_id', '=', journal.company_id.id),
                    ('id', '!=', journal.id),
                ])
                if duplicate:
                    raise UserError(_(
                        'Company "%s" already has an eWallet journal configured (%s). '
                        'Please disable it before enabling another.'
                    ) % (journal.company_id.name, duplicate[0].name))
        return res


class AccountMoveWallet(models.Model):
    _inherit = 'account.move'

    # ── helpers ──────────────────────────────────────────────────────────────

    def _wink_get_wallet_journal(self):
        """Return the eWallet journal for the current company, or empty recordset."""
        return self.env['account.journal'].search(
            [('is_ewallet_journal', '=', True), ('company_id', '=', self.env.company.id)],
            limit=1,
        )

    # ── Reset to Draft: cancel the linked wallet transaction ─────────────────

    def _wink_cancel_wallet_txns(self):
        """Cancel any done wallet transactions linked to moves in self.

        Uses move_id linkage (not journal filter) so that both top-up JVs
        (posted on bank/cash journal) and payment JVs (posted on WEWL journal)
        are caught when cancelled or reset to draft.
        """
        self.env['kuec.wallet.transaction'].search([
            ('move_id', 'in', self.ids),
            ('state', '=', 'done'),
        ]).write({'state': 'cancelled'})

    def button_draft(self):
        """When any wallet JV is reset to draft, cancel the linked wallet transaction."""
        self._wink_cancel_wallet_txns()
        return super().button_draft()

    def button_cancel(self):
        """When any wallet JV is cancelled, cancel the linked wallet transaction.

        Covers both top-up JVs (on bank journal) and payment JVs (on WEWL journal).
        """
        self._wink_cancel_wallet_txns()
        return super().button_cancel()

    # ── Reverse Entry: create a refund wallet transaction when reversal posts ─

    def action_post(self):
        """After posting, if this is a WEWL reversal JV, create a refund wallet transaction.

        When a coordinator reverses a wallet payment via "Reverse Entry", Odoo posts
        a new JV (DR AR / CR WEWL). This hook detects that new JV and:
            1. Creates a kuec.wallet.transaction of type 'refund' (positive amount)
               to restore the customer's wallet balance.
            2. Marks the original wallet transaction as 'cancelled' to avoid
               double-counting.

        Workflow:
            1. Call super() to post the move(s).
            2. Filter for WEWL-journal moves that have a reversed_entry_id set.
            3. For each, find the original wallet transaction via move_id.
            4. Create a refund transaction and cancel the original.
        """
        res = super().action_post()
        wallet_journal = self._wink_get_wallet_journal()
        if not wallet_journal:
            return res
        reversal_moves = self.filtered(
            lambda m: m.journal_id == wallet_journal and m.reversed_entry_id
        )
        for reversal in reversal_moves:
            original_txn = self.env['kuec.wallet.transaction'].search([
                ('move_id', '=', reversal.reversed_entry_id.id),
            ], limit=1)
            if not original_txn:
                continue
            # Idempotency: skip if a refund transaction for this reversal already exists
            if self.env['kuec.wallet.transaction'].search([
                ('move_id', '=', reversal.id),
                ('transaction_type', '=', 'refund'),
            ], limit=1):
                continue
            # Create refund transaction to restore balance
            self.env['kuec.wallet.transaction'].create({
                'partner_id': original_txn.partner_id.id,
                'transaction_type': 'refund',
                'amount': -original_txn.amount,   # original was negative → refund is positive
                'description': _('Reversal: %s') % original_txn.description,
                'currency_id': original_txn.currency_id.id,
                'move_id': reversal.id,
                'order_id': original_txn.order_id.id if original_txn.order_id else False,
            })
            # Cancel the original debit so balance is not double-counted
            original_txn.write({'state': 'cancelled'})
        return res

    # GOV-001: Auto-activate entitlement when gov charge invoice is fully paid.
    # Use _write() not write(): in Odoo 18, stored computed fields (payment_state) are
    # flushed via _write() directly, bypassing the ORM write() override. _write() is
    # called both by the ORM write() path and by the computed field flush path.
    def _write(self, vals):
        res = super()._write(vals)
        if 'payment_state' in vals and vals.get('payment_state') in ('paid', 'in_payment'):
            for move in self:
                entitlement = self.env['wink.bundle.entitlement'].sudo().search([
                    ('wink_gov_charge_invoice_id', '=', move.id),
                ], limit=1)
                if not entitlement:
                    continue
                # Check via raw SQL: if wink_gov_charge_invoice_id is cleared, activation
                # already completed (action_gov_charge_paid clears it AFTER successful activation).
                self.env.cr.execute(
                    "SELECT wink_gov_charge_invoice_id FROM wink_bundle_entitlement WHERE id = %s",
                    (entitlement.id,)
                )
                row = self.env.cr.fetchone()
                if not row or not row[0]:
                    continue  # Already activated — invoice link already cleared
                try:
                    entitlement.sudo().action_gov_charge_paid()
                except Exception:
                    logging.getLogger(__name__).warning(
                        "GOV-001: Failed to auto-activate entitlement %s after gov charge payment on invoice %s",
                        entitlement.id, move.id, exc_info=True,
                    )
                    try:
                        if entitlement.order_id:
                            entitlement.order_id.sudo().message_post(
                                body=(
                                    'GOV-001 Warning: Auto-activation of <b>%s</b> failed after '
                                    'gov charge payment. Please check server logs and manually activate.'
                                ) % (entitlement.name or ''),
                                message_type='comment',
                                subtype_xmlid='mail.mt_note',
                            )
                    except Exception:
                        pass
        return res

    def action_open_wallet_payment(self):
        """Open the eWallet payment wizard pre-filled with this invoice and its customer.

        Only applicable to posted customer invoices with an outstanding balance.

        Returns:
            dict: Window action opening the wizard in dialog mode.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pay Using eWallet'),
            'res_model': 'wink.wallet.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_invoice_id': self.id,
                'default_currency_id': self.currency_id.id,
            },
        }


class PaymentTransactionGovCharge(models.Model):
    """GOV-001: Hook into payment gateway reconciliation to auto-activate bundle services.

    _reconcile_after_done() is called by Odoo immediately after a payment.transaction
    is confirmed and its invoices are reconciled. This is the most reliable hook for
    online payment gateway flows (Stripe, PayTabs, etc.) and covers the case where
    _write() on account.move does not fire synchronously.
    """

    _inherit = 'payment.transaction'

    def _reconcile_after_done(self):
        """Trigger GOV-001 auto-activation after payment gateway reconciles gov charge invoice.

        Workflow:
            1. Call super() — payment is created and reconciled with invoice.
            2. For each reconciled invoice, check if it is a gov charge invoice
               linked to a bundle entitlement that has not yet been activated.
            3. Call action_gov_charge_paid() to clear the invoice link and activate.
        """
        res = super()._reconcile_after_done()
        import logging as _log
        _logger = _log.getLogger(__name__)
        for tx in self:
            for invoice in tx.invoice_ids:
                if invoice.payment_state not in ('paid', 'in_payment'):
                    continue
                entitlement = self.env['wink.bundle.entitlement'].sudo().search([
                    ('wink_gov_charge_invoice_id', '=', invoice.id),
                ], limit=1)
                # Skip if invoice link already cleared — activation already completed
                if not entitlement or not entitlement.wink_gov_charge_invoice_id:
                    continue
                try:
                    entitlement.sudo().action_gov_charge_paid()
                    _logger.info(
                        "GOV-001: Auto-activated entitlement %s (%s) after payment gateway payment.",
                        entitlement.id, entitlement.name,
                    )
                except Exception:
                    _logger.warning(
                        "GOV-001: Auto-activation failed for entitlement %s after gateway payment on invoice %s.",
                        entitlement.id, invoice.id, exc_info=True,
                    )
        return res

    def _get_landing_route(self):
        """Redirect to the bundle request page after paying a gov charge invoice.

        If this transaction is linked to a gov charge invoice, return the
        request detail URL so the customer lands back on their request page
        (with the service already activated) instead of the generic /payment/status page.

        Returns:
            str: URL to redirect to after payment completes.
        """
        for invoice in self.invoice_ids:
            entitlement = self.env['wink.bundle.entitlement'].sudo().search([
                ('wink_gov_charge_invoice_id', '=', invoice.id),
            ], limit=1)
            if entitlement and entitlement.order_id:
                return '/my/requests/%d?gov_paid=1' % entitlement.order_id.id
        return super()._get_landing_route()
