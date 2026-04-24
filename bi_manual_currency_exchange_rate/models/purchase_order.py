# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    """
    Extension of `purchase.order` to include manual currency rate controls.

    The manual rate fields allow users to define and activate a custom exchange rate
    that should be used throughout the purchase order lifecycle—including pricing
    and invoice preparation.
    """
    _inherit = 'purchase.order'

    purchase_manual_currency_rate = fields.Float(
        string='Currency Rate',
        default=lambda self: self.expected_currency_rate,
        copy=False,
        digits=0,
        help="""
            Define the manual currency rate to apply to product pricing 
            and invoice generation when the above option is active.
            """
    )

    expected_currency_rate = fields.Float(
        compute="_compute_expected_currency_rate",
        digits=0,
    )

    @api.depends('order_line.price_subtotal', 'company_id', 'purchase_manual_currency_rate')
    def _amount_all(self):
        AccountTax = self.env['account.tax']
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )
            order.amount_untaxed = tax_totals['base_amount_currency']
            order.amount_tax = tax_totals['tax_amount_currency']
            order.amount_total = tax_totals['total_amount_currency']
            if order.currency_id != order.company_currency_id and order.purchase_manual_currency_rate > 0:
                order.amount_total_cc = tax_totals[
                                            'total_amount_currency'] / order.purchase_manual_currency_rate
            else:
                order.amount_total_cc = tax_totals['total_amount_currency']

    def copy(self, default=None):
        ctx = dict(self.env.context)
        ctx.update({'default_purchase_manual_currency_rate': self.expected_currency_rate})
        self = self.with_context(ctx)
        return super().copy(default=default)

    @api.constrains('purchase_manual_currency_rate')
    def _check_currency_rate(self):
        """Ensure the currency rate is strictly positive when record's currency differs from company currency."""
        for rec in self:
            if (
                    rec.currency_id
                    and rec.company_id
                    and rec.currency_id != rec.company_currency_id
                    and rec.purchase_manual_currency_rate <= 0
            ):
                raise ValidationError(_("The currency rate must be strictly positive."))

    @api.onchange('currency_id', 'company_id')
    def _onchange_currency_id_set_manual_rate(self):
        """
        When the currency or company changes, suggest the standard
        conversion rate in the manual rate field.
        """
        self.purchase_manual_currency_rate = self.expected_currency_rate

    def get_currency_rate(self, company_id, to_currency_id, date):
        company = self.env['res.company'].browse(company_id)
        to_currency = self.env['res.currency'].browse(to_currency_id)

        return self.env['res.currency']._get_conversion_rate(
            from_currency=company.currency_id,
            to_currency=to_currency,
            company=company,
            date=date,
        )

    def refresh_currency_rate(self):
        for po in self:
            po.purchase_manual_currency_rate = po.expected_currency_rate

    @api.depends('currency_id', 'company_currency_id', 'company_id')
    def _compute_expected_currency_rate(self):
        for po in self:
            if po.currency_id:
                po.expected_currency_rate = po.env['res.currency']._get_conversion_rate(
                    from_currency=po.company_currency_id,
                    to_currency=po.currency_id,
                    company=po.company_id,
                    date=fields.Date.context_today(self),
                )
            else:
                po.expected_currency_rate = 1

    def _prepare_invoice(self):
        """
        Propagates manual currency rate fields to the vendor bill generated from the PO.

        Returns:
            dict: invoice values to be passed to the account.po create process.
        """
        res = super()._prepare_invoice()
        if self.purchase_manual_currency_rate:
            res.update({
                'invoice_currency_rate': self.purchase_manual_currency_rate,
            })
        return res
