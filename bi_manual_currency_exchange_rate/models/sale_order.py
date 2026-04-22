# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    """
    Extension of the core `sale.order` model to support manual currency rate handling.

    This is particularly useful for international transactions where a fixed exchange rate is used
    instead of relying on Odoo's real-time currency conversion.

    Fields:
        - sale_manual_currency_rate_active: Boolean flag to enable manual FX.
        - sale_manual_currency_rate: Manually defined exchange rate used when the flag is enabled.
    """
    _inherit = 'sale.order'

    sale_manual_currency_rate = fields.Float(
        string='Currency Rate',
        copy=False,
        default=lambda self: self.expected_currency_rate,
        digits=0,
        help="""Define the manual currency rate to apply to product pricing 
                    and invoice generation when the above option is active.
                    """
    )
    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        tracking=True,
        required=True,
        compute='_compute_currency_id', inverse='_inverse_currency_id', store=True, readonly=False,
        precompute=True,
    )

    expected_currency_rate = fields.Float(
        compute="_compute_expected_currency_rate",
        digits=0,
    )

    def copy(self, default=None):
        ctx = dict(self.env.context)
        ctx.update({'default_sale_manual_currency_rate' : self.expected_currency_rate})
        self = self.with_context(ctx)
        return super().copy(default=default)

    @api.constrains('sale_manual_currency_rate')
    def _check_currency_rate(self):
        """Ensure the currency rate is strictly positive when record's currency differs from company currency."""
        for rec in self:
            if (
                    rec.currency_id
                    and rec.company_id
                    and rec.currency_id != rec.company_currency_id
                    and rec.sale_manual_currency_rate <= 0
            ):
                raise ValidationError(_("The currency rate must be strictly positive."))

    @api.onchange('currency_id', 'company_id')
    def _onchange_currency_id_set_manual_rate(self):
        """
        When the currency or company changes, suggest the standard
        conversion rate in the manual rate field.
        """
        self.sale_manual_currency_rate = self.expected_currency_rate

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for so in self:
            currency = (
                    so.journal_id.currency_id
                    or so.currency_id
                    or so.journal_id.company_id.currency_id
                    or so.company_currency_id
            )
            so.currency_id = currency

    @api.onchange('currency_id')
    def _inverse_currency_id(self):
        self.order_line._conditional_add_to_compute(
            'currency_id',
            lambda l: l.order_id.currency_id != l.currency_id
        )


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
        for so in self:
            so.sale_manual_currency_rate = so.expected_currency_rate

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

    def _prepare_invoice(self):
        """
        Override of `_prepare_invoice` to propagate manual currency rate settings to the generated invoice.

        Returns:
            dict: The invoice values including manual FX settings if active.
        """
        res = super()._prepare_invoice()
        res.update({
            'invoice_currency_rate': self.sale_manual_currency_rate
        })
        return res
