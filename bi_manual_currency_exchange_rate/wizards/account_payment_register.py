# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    """
        Extension of the 'account.payment.register' wizard.

        Introduces additional fields and overrides default methods to ensure that manual exchange rates
        are respected during the payment registration process for invoices. This includes validating
        consistency between multiple selected invoices, applying manual rates in calculations,
        and propagating these values during payment creation.
        """
    _inherit = 'account.payment.register'

    def _get_default_manual_currency_rate(self):
        force_manual_currency_rate = self._context.get('force_manual_currency_rate', False)
        default_manual_currency_rate = self._context.get('default_manual_currency_rate', 0)
        manual_currency_rate = self._context.get('manual_currency_rate', 1)
        if force_manual_currency_rate and default_manual_currency_rate or manual_currency_rate:
            return default_manual_currency_rate or manual_currency_rate
        return self.expected_currency_rate or 1

    manual_currency_rate = fields.Float(
        'Rate',
        # default=lambda self: self.expected_currency_rate or 1,
        default=_get_default_manual_currency_rate,
        copy=False,
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

    def get_currency_rate(self, company_id, to_currency_id, date):
        company = self.env['res.company'].browse(company_id)
        to_currency = self.env['res.currency'].browse(to_currency_id)

        return self.env['res.currency']._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=to_currency,
            company=company,
            date=date,
        )

    @api.depends('currency_id', 'company_currency_id', 'company_id')
    def _compute_expected_currency_rate(self):
        for so in self:
            if so.currency_id:
                so.expected_currency_rate = so.env['res.currency']._get_conversion_rate(
                    from_currency=so.company_currency_id,
                    to_currency=so.currency_id,
                    company=so.company_id,
                    date=fields.Date.context_today(self),
                ) or 1
            else:
                so.expected_currency_rate = 1

    @api.model
    def default_get(self, default_fields):
        """
                Overrides default_get to preload manual currency rate fields if present on selected invoices.

                Validates:
                - All selected invoices must either have manual currency rate active or not.
                - All selected invoices must have the same manual rate if enabled.

                Returns:
                    dict: Default values for the payment registration wizard, including manual rate fields.
                """
        rec = super().default_get(default_fields)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec
        invoices = self.env['account.move'].browse(active_ids).filtered(
            lambda move: move.is_invoice(include_receipts=True))
        if len(invoices or []) > 1:
            if all(inv.currency_id != inv.company_currency_id for inv in invoices):
                return rec
            if any(inv.currency_id != inv.company_currency_id for inv in invoices):
                raise ValidationError(
                    _("Selected invoice to make payment have not similer currency or currency rate is not same.\n Make sure selected invoices have same currency and same manual currency rate."))
            else:
                rate = invoices[0].manual_currency_rate
                if any(inv.manual_currency_rate != rate for inv in invoices):
                    raise ValidationError(
                        _("Selected invoice to make payment have not similer currency or currency rate is not same.\n Make sure selected invoices have same currency and same manual currency rate."))
        force_manual_currency_rate = self._context.get('force_manual_currency_rate', False)
        if force_manual_currency_rate:
            manual_currency_rate = self._context.get('manual_currency_rate') or 1
        else:
            manual_currency_rate = invoices[0].manual_currency_rate or 1

        rec.update({
            'manual_currency_rate': manual_currency_rate
        })
        return rec

    def _create_payment_vals_from_wizard(self, batch_result):
        """
               Passes manual currency fields into the dictionary used to create the payment object.

               Args:
                   batch_result (dict): Batch data from wizard.

               Returns:
                   dict: Payment creation values including manual rate if enabled.
               """
        vals = super()._create_payment_vals_from_wizard(batch_result)
        if self.currency_id != self.company_currency_id:
            vals.update({
                'manual_currency_rate': self.manual_currency_rate
            })
        return vals

    @api.depends('can_edit_wizard', 'source_amount', 'source_amount_currency',
                 'source_currency_id', 'company_id', 'currency_id', 'payment_date',
                 'manual_currency_rate')
    def _compute_amount(self):
        """
               Triggers recomputation of wizard amounts considering manual rate.
               This method leverages the super method, but gets called when related fields change.
               """
        return super()._compute_amount()

    @api.depends('can_edit_wizard', 'amount', 'manual_currency_rate')
    def _compute_payment_difference(self):
        """
                Ensures payment difference gets recomputed if the manual rate toggles or changes.
                """
        return super()._compute_payment_difference()

    def _get_total_amount_in_wizard_currency_to_full_reconcile(self, batch_result,
                                                               early_payment_discount=True):
        """ Compute the total amount needed in the currency of the wizard to fully reconcile the batch of journal
        items passed as parameter.

        :param batch_result:    A batch returned by '_get_batches'.
        :return:                An amount in the currency of the wizard.
        """
        self.ensure_one()
        comp_curr = self.company_id.currency_id

        if self.source_currency_id == self.currency_id:
            # Same currency (manage the early payment discount).
            return self._get_total_amount_using_same_currency(batch_result,
                                                              early_payment_discount=early_payment_discount)
        elif self.source_currency_id != comp_curr and self.currency_id == comp_curr:
            # Foreign currency on source line but the company currency one on the opposite line.
            if self.currency_id != self.company_currency_id and self.manual_currency_rate:
                return (self.source_amount_currency / self.manual_currency_rate), False
            else:
                return self.source_currency_id._convert(
                    self.source_amount_currency,
                    comp_curr,
                    self.company_id,
                    self.payment_date,
                ), False
        elif self.source_currency_id == comp_curr and self.currency_id != comp_curr:
            # Company currency on source line but a foreign currency one on the opposite line.
            if self.currency_id != self.company_currency_id and self.manual_currency_rate:
                return abs(sum((aml.amount_residual * self.manual_currency_rate) for aml in
                               batch_result['lines']
                               )), False
            else:
                return abs(sum(
                    comp_curr._convert(
                        aml.amount_residual,
                        self.currency_id,
                        self.company_id,
                        aml.date,
                    )
                    for aml in batch_result['lines']
                )), False
        else:
            # Foreign currency on payment different than the one set on the journal entries.
            if self.currency_id != self.company_currency_id and self.manual_currency_rate:
                return self.source_amount * self.manual_currency_rate, False
            else:
                return comp_curr._convert(
                    self.source_amount,
                    self.currency_id,
                    self.company_id,
                    self.payment_date,
                ), False

    # def _create_payment_vals_from_wizard(self, batch_result):
    #     payment_vals = {
    #         'date': self.payment_date,
    #         'amount': self.amount,
    #         'payment_type': self.payment_type,
    #         'partner_type': self.partner_type,
    #         'memo': self.communication,
    #         'journal_id': self.journal_id.id,
    #         'currency_id': self.currency_id.id,
    #         'partner_id': self.partner_id.id,
    #         'partner_bank_id': self.partner_bank_id.id,
    #         'payment_method_line_id': self.payment_method_line_id.id,
    #         'destination_account_id': self.line_ids[0].account_id.id,
    #         'manual_currency_rate': self.manual_currency_rate,
    #         'write_off_line_vals': [],
    #     }
    #
    #     print(1)
    #
    #     if self.currency_id != self.company_currency_id and self.manual_currency_rate:
    #         conversion_rate = self.manual_currency_rate
    #     else:
    #         conversion_rate = self.env['res.currency']._get_conversion_rate(
    #             self.currency_id,
    #             self.company_id.currency_id,
    #             self.company_id,
    #             self.payment_date,
    #         )
    #
    #     print(2)
    #
    #     print('self.payment_difference_handling', self.payment_difference_handling)
    #
    #     if self.payment_difference_handling == 'reconcile':
    #
    #         if self.early_payment_discount_mode:
    #             epd_aml_values_list = []
    #             for aml in batch_result['lines']:
    #                 if aml._is_eligible_for_early_payment_discount(self.currency_id,
    #                                                                self.payment_date):
    #                     epd_aml_values_list.append({
    #                         'aml': aml,
    #                         'amount_currency': -aml.amount_residual_currency,
    #                         'balance': aml.company_currency_id.round(
    #                             -aml.amount_residual_currency * conversion_rate),
    #                     })
    #
    #             open_amount_currency = self.payment_difference * (
    #                 -1 if self.payment_type == 'outbound' else 1)
    #             open_balance = self.company_id.currency_id.round(
    #                 open_amount_currency * conversion_rate)
    #             early_payment_values = self.env[
    #                 'account.move']._get_invoice_counterpart_amls_for_early_payment_discount(
    #                 epd_aml_values_list, open_balance)
    #             for aml_values_list in early_payment_values.values():
    #                 payment_vals['write_off_line_vals'] += aml_values_list
    #
    #         elif not self.currency_id.is_zero(self.payment_difference):
    #             if self.payment_type == 'inbound':
    #                 # Receive money.
    #                 write_off_amount_currency = self.payment_difference
    #             else:
    #                 # Send money.
    #                 write_off_amount_currency = -self.payment_difference
    #
    #             write_off_balance = self.company_id.currency_id.round(
    #                 write_off_amount_currency * conversion_rate)
    #             # payment_vals['write_off_line_vals'].append({
    #             #     'name': self.writeoff_label,
    #             #     'account_id': self.writeoff_account_id.id,
    #             #     'partner_id': self.partner_id.id,
    #             #     'currency_id': self.currency_id.id,
    #             #     'amount_currency': write_off_amount_currency,
    #             #     'balance': write_off_balance,
    #             # })
    #
    #     return payment_vals
