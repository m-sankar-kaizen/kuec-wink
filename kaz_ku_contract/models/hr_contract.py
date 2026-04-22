# -*- coding: utf-8 -*-
from odoo import models, fields


class HRContract(models.Model):
    """
    Extends the `hr.contract` model to include additional monetary fields related to allowances and deductions.

    This extension supports government or institutional payroll scenarios that require precise breakdowns of
    both involuntary and voluntary deductions as well as various types of employee allowances.

    Fields
    ======

    ALLOWANCES:
    -----------
    - acting_allowance: Monetary field representing acting position compensation.
    - child_allowance: Financial support provided per child or as a child-related subsidy.
    - cost_of_living_subsidy: Adjustment allowance to compensate for inflation or living cost increases.
    - market_differential: Supplement to compensate salary competitiveness in specific markets.
    - rounding: Payroll rounding difference adjustment.
    - vacation_allowance: Monetary benefit given as part of or in place of paid vacation.
    - ded_acting_allowance_unpaid: Deduction applied to reverse acting allowance during unpaid periods.
    - pension_employee_adjustment_oman: Adjustment specific to Oman’s employee pension calculations.

    DEDUCTIONS:
    ===========
    INVOLUNTARY DEDUCTIONS:
    -----------------------
    - pention_employee_contribution_oman: Mandatory pension contribution by the employee under Oman regulations.
    - pention_employee_contribution_uae: Mandatory pension contribution by the employee under UAE regulations.

    VOLUNTARY DEDUCTIONS:
    ---------------------
    - ded_housing_advance: Housing loan installment deducted from salary.
    - ded_housing_advance_next_year: Pre-arranged housing advance deduction to start next fiscal year.
    - ded_other_recovery_wb: Other voluntary or internal recovery deductions (WB = Work Benefit or Welfare Board).

    Currency
    ========
    All monetary fields rely on the `currency_id` defined in the `hr.contract` model to maintain consistency
    across multi-currency environments.

    Usage
    =====
    These fields are typically consumed in payroll computation rules (`hr.salary.rule`),
    employee payslip generation (`hr.payslip`), or salary analysis reports.
    """
    _inherit = 'hr.contract'

    # Allowance Fields
    acting_allowance = fields.Monetary(currency_field='currency_id')
    child_allowance = fields.Monetary(currency_field='currency_id')
    cost_of_living_subsidy = fields.Monetary(currency_field='currency_id')
    market_differential = fields.Monetary(currency_field='currency_id')
    rounding = fields.Monetary(currency_field='currency_id')
    vacation_allowance = fields.Monetary(currency_field='currency_id')
    ded_acting_allowance_unpaid = fields.Monetary(
        currency_field='currency_id',
        string="Acting Allowance Unpaid"
    )
    pension_employee_adjustment_oman = fields.Monetary(
        currency_field='currency_id',
        string="Pension Employee Adjustment Oman"
    )

    # Involuntary Deduction Fields
    pention_employee_contribution_oman = fields.Monetary(currency_field='currency_id')
    pention_employee_contribution_uae = fields.Monetary(currency_field='currency_id')

    # Voluntary Deduction Fields
    ded_housing_advance = fields.Monetary(currency_field='currency_id')
    ded_housing_advance_next_year = fields.Monetary(currency_field='currency_id')
    ded_other_recovery_wb = fields.Monetary(currency_field='currency_id')
