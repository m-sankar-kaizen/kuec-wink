# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MaterialPurchaseRequisitionLine(models.Model):
    """
    Inherits material.purchase.requisition.line to add analytic distribution validation,
    automatic analytic assignment based on departments, currency conversion logic,
    subtotal/amount computation, and budget control mechanisms for requisition lines.
    """
    _inherit = "material.purchase.requisition.line"

    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        required=False,
        help="Expense account to be used for this requisition line."
    )

    analytic_distribution = fields.Json(
        required=True,
        help="Distribution of the line amount across analytic accounts in percentage."
    )

    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get(
            "Percentage Analytic"),
        help="Decimal precision used to round analytic percentages."
    )

    change_count = fields.Boolean(
        string='Change_count',
        required=False,
        help="Flag used internally to prevent recursive auto-filling of analytics."
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='requisition_id.currency_id',
        store=True,
        help="Currency used in the requisition."
    )

    amount_incurrency = fields.Float(
        string='Total Amount in Currency',
        compute='_compute_amount_incurrency',
        store=True,
        help="Total line amount in the selected currency."
    )

    subtotal = fields.Float(
        string='Subtotal',
        compute='compute_sub_total',
        store=True,
        help="Total before currency conversion (qty * unit price)."
    )

    requisition_type = fields.Selection(
        selection=[('purchase', 'Purchase Order')],
        string='Requisition Action',
        default='purchase',
        required=True,
        help="Defines what action will be created from this requisition line."
    )

    price_unit = fields.Float(
        string='Price Unit',
        required=False,
        help="Unit price of the product."
    )

    @api.constrains('analytic_distribution')
    def check_distribution_sum(self):
        """
        Ensure that the analytic distribution dictionary adds up to 100%.
        Raises:
            ValidationError: If the sum is not equal to 100%.
        """
        for line in self:
            if not line._check_one_hundred_percent(line.analytic_distribution):
                raise ValidationError(
                    _("Analytic distribution sum in each line must equal 100%"))

    @api.model
    def _check_one_hundred_percent(self, analytic_dict=None):
        """
        Helper method to verify if the sum of analytic percentages equals 100%.

        Args:
            analytic_dict (dict): Analytic account ID to percentage mapping.

        Returns:
            bool: True if total equals 100, False otherwise.
        """
        if analytic_dict is None:
            analytic_dict = {}

        total = 0
        for val in analytic_dict.values():
            total += round(val, 2)
        return total == 100

    def _get_line_residual_after_distribution(self):
        """
        Compute the residual amount left after analytic distribution.
        Currently returns total line amount since deduction is commented out.

        Returns:
            float: Residual amount (or 0 if negative).
        """
        amount = self.qty * self.price_unit
        residual = amount
        return residual if residual > 0 else 0

    def _get_analytic_accounts_amounts(self):
        """
        Computes the total budgeted amount per analytic account for this line.

        Returns:
            dict: {analytic_account_id: amount}
        """
        analytic_dict = {}
        for line in self:
            amount = line.qty * line.price_unit
            if line.analytic_distribution:
                for analytic_id, percent in line.analytic_distribution.items():
                    analytic_dict[analytic_id] = analytic_dict.get(analytic_id,
                                                                   0) + (
                                                         percent / 100) * amount
        return analytic_dict

    def _get_accounts_residual_amount(self):
        """
        Computes the residual (non-distributed) budget amount per account.

        Returns:
            dict: {account_id: amount}
        """
        accounts_dict = {}
        for line in self:
            if line.account_id:
                residual_amount = line._get_line_residual_after_distribution()
                accounts_dict[line.account_id.id] = accounts_dict.get(
                    line.account_id.id, 0) + residual_amount
        return accounts_dict

    def _compute_budget_limit(self):
        """
        Placeholder for budget validation logic at the line level.
        Not implemented yet.
        """
        pass

    @api.depends('product_id', 'qty', 'price_unit', 'currency_id')
    def compute_sub_total(self):
        """Computes the line subtotal (qty × price_unit)."""
        for rec in self:
            rec.subtotal = rec.qty * rec.price_unit

    @api.depends('product_id', 'qty', 'price_unit', 'currency_id',
                 'requisition_id.purchase_manual_currency_rate')
    def _compute_amount_incurrency(self):
        """
        Compute line amount based on whether the line currency differs from company currency.
        Applies manual currency rate if needed.
        """
        for line in self:
            amount = 0
            if self.currency_id:
                if self.currency_id.id == self.env.company.currency_id.id:
                    amount += line.qty * line.price_unit
                else:
                    amount += line.qty * line.price_unit * line.requisition_id.purchase_manual_currency_rate
            line.amount_incurrency = amount

    @api.onchange('product_id')
    def _onchange_product_line(self):
        """
        Automatically distribute 100% of the amount among the departments’ analytic accounts
        when a product is selected and `change_count` is False.
        """
        if not self.change_count:
            if self.requisition_id.department_ids:
                analytics = self.requisition_id.department_ids.mapped(
                    'analytic_account_id.id')
                if analytics:
                    total_lines = len(analytics)
                    percent = round(100.0 / total_lines, 2)
                    percentages = [percent] * total_lines
                    total_percentage = sum(percentages)
                    difference = round(100.0 - total_percentage, 2)
                    if difference != 0:
                        percentages[0] += difference
                    analytic_dict = {str(analytics[i]): percentages[i] for i in
                                     range(total_lines)}
                    self.analytic_distribution = analytic_dict
                    return
            self.analytic_distribution = {}
            self.change_count = True

    @api.constrains('product_id', 'description', 'qty', 'uom',
                    'requisition_type', 'price_unit')
    def set_vendor_constraint(self):
        """Sets vendor based on linked requisition if available (for constraint compatibility)."""
        if self.requisition_id and self.requisition_id.purchase_vendor_ids:
            self.partner_id = self.requisition_id.purchase_vendor_ids.ids

    @api.onchange('product_id', 'description', 'qty', 'uom', 'requisition_type',
                  'price_unit')
    def set_vendor_from_requisition(self):
        """Set vendor from requisition when values change on the line."""
        if self.requisition_id and self.requisition_id.purchase_vendor_ids:
            self.partner_id = self.requisition_id.purchase_vendor_ids.ids

    @api.onchange('product_id')
    def onchange_prod(self):
        """
        Automatically fill the account_id from product or its category when product is selected.
        """
        if self.product_id and self.product_id.property_account_expense_id:
            self.account_id = self.product_id.property_account_expense_id.id
        elif self.product_id and self.product_id.categ_id and self.product_id.categ_id.property_account_expense_categ_id:
            self.account_id = self.product_id.categ_id.property_account_expense_categ_id.id

    @api.constrains('analytic_distribution', 'account_id')
    def constrain_account_to_analytic(self):
        """
        Validates that the selected account is covered by a budget for the specified analytic distribution.
        Raises:
            ValidationError: If budget is not allocated for this account-analytic combination.
        """
        for rec in self:
            existed = True
            if rec.account_id and rec.analytic_distribution:

                budget_lines = self.env[
                    'budget.line'].sudo().search([
                    ('date_from', '<=', self.requisition_id.request_date),
                    ('date_to', '>=', self.requisition_id.request_date),
                    ('company_id', '=', rec.company_id.id),
                    ('budget_analytic_id.state', 'not in',
                     ['canceled', 'draft'])
                ])

                existed = False
                keys_list = [int(i) for k in rec.analytic_distribution.keys() for i in k.split(',')]

                for line in budget_lines:
                    fnames = line._get_plan_fnames()
                    analytic_accounts = [line[fname].id for fname in fnames if
                                         line[fname]]

                    if (rec.account_id.id in line.general_budget_id.account_ids.ids) and (any(x in keys_list for x in analytic_accounts)):
                        existed = True
                        break
                if not existed:
                    raise ValidationError(_(
                        f"The account selected ({rec.account_id.display_name}) on the line "
                        f"does not have a budget allocated for the selected Cost Centers "
                        f"({rec.get_analytic_accounts_name()})"
                    ))

    def write(self, vals):
        """
        Override write to enforce post-write budget validation.
        """
        res = super(MaterialPurchaseRequisitionLine, self).write(vals)
        self.constrain_account_to_analytic()
        return res

    def get_analytic_accounts_name(self):
        """
        Utility to get a human-readable list of analytic account names based on distribution.

        Returns:
            str: Comma-separated display names of analytic accounts.
        """
        analytic_ids = [int(x) for key in self.analytic_distribution.keys() for x
                        in key.split(',')]
        analytic_accounts = self.env['account.analytic.account'].sudo().search(
            [('id', 'in', analytic_ids)])
        return ",".join(analytic_accounts.mapped('display_name'))
