# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    """
        Extension of the actual `account.payment` model to apply manual exchange rate
        logic to journal entry creation and payment difference computations.
        """
    _inherit = "account.payment"

    manual_currency_rate = fields.Float(
        'Rate',
        copy=False,
        default=lambda self: self.expected_currency_rate,
        digits=0
    )

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True,
    )
    expected_currency_rate = fields.Float(
        compute="_compute_expected_currency_rate",
        digits=0,
    )

    def copy(self, default=None):
        ctx = dict(self.env.context)
        ctx.update({'default_manual_currency_rate' : self.expected_currency_rate})
        self = self.with_context(ctx)
        return super().copy(default=default)

    @api.constrains('manual_currency_rate')
    def _check_currency_rate(self):
        """Ensure the currency rate is strictly positive when record's currency differs from company currency."""
        for rec in self:
            if (
                    rec.currency_id
                    and rec.company_id
                    and rec.currency_id != rec.company_currency_id
                    and rec.manual_currency_rate <= 0
            ):
                raise ValidationError(_("The currency rate must be strictly positive."))

    @api.onchange('currency_id', 'company_id')
    def _onchange_currency_id_set_manual_rate(self):
        """
        When the currency or company changes, suggest the standard
        conversion rate in the manual rate field.
        """
        self.manual_currency_rate = self.expected_currency_rate

    def refresh_currency_rate(self):
        for so in self:
            so.manual_currency_rate = so.expected_currency_rate

    @api.depends('currency_id', 'company_currency_id', 'company_id')
    def _compute_expected_currency_rate(self):
        for so in self:
            if so.currency_id:
                so.expected_currency_rate = so.env['res.currency']._get_conversion_rate(
                    from_currency=so.company_currency_id,
                    to_currency=so.currency_id,
                    company=so.company_id,
                    date=fields.Date.context_today(self),
                )
            else:
                so.expected_currency_rate = 1

    def get_currency_rate(self, company_id, to_currency_id, date):
        company = self.env['res.company'].browse(company_id)
        to_currency = self.env['res.currency'].browse(to_currency_id)

        return self.env['res.currency']._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=to_currency,
            company=company,
            date=date,
        )

    @api.model
    def default_get(self, default_fields):
        """
                Preload manual rate fields from the first selected invoice during payment creation.

                Returns:
                    dict: Default values including manual rate fields.
                """
        rec = super().default_get(default_fields)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec
        invoices = self.env['account.move'].browse(active_ids).filtered(
            lambda move: move.is_invoice(include_receipts=True))
        if invoices:
            rec.update({
                'manual_currency_rate': invoices[0].invoice_currency_rate
            })
        return rec

    @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id', 'payment_type',
                 'manual_currency_rate')
    def _compute_payment_difference(self):
        """
                Recompute payment difference taking into account any manual exchange rate changes.
                """
        return super()._compute_payment_difference()

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional list of dictionaries to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or []

        if not self.outstanding_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
                self.payment_method_line_id.name, self.journal_id.display_name))

        # Compute amounts.
        write_off_line_vals_list = write_off_line_vals or []
        write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
        write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
        else:
            liquidity_amount_currency = 0.0

        if self.currency_id != self.company_currency_id and self.manual_currency_rate > 0:
            currency_rate = self.company_id.currency_id.rate / self.manual_currency_rate
            liquidity_balance = liquidity_amount_currency * currency_rate
            if force_balance is not None:
                sign = 1 if liquidity_amount_currency > 0 else -1
                liquidity_balance = sign * abs(force_balance)
            counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
            write_off_balance = write_off_amount_currency * currency_rate
            counterpart_balance = -liquidity_balance - write_off_balance
            currency_id = self.currency_id.id

        else:
            liquidity_balance = self.currency_id._convert(
                liquidity_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
            counterpart_balance = -liquidity_balance - write_off_balance
            currency_id = self.currency_id.id

        # Compute a default label to set on the journal items.
        liquidity_line_name = ''.join(
            x[1] for x in self._get_aml_default_display_name_list() if x[1])
        counterpart_line_name = liquidity_line_name

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.outstanding_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': counterpart_line_name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
            },
        ]
        return line_vals_list + write_off_line_vals_list
