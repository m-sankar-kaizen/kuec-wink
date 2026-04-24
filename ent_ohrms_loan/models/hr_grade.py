# -*- coding: utf-8 -*-
from odoo import models, fields


class HrGrade(models.Model):
    """
    Inherits:
        hr.grade

    Purpose:
        Extends the `hr.grade` model to support housing advance policy configurations
        and linkage with loan records.

    Main Additions:
    1. is_housing_advance (Boolean):
        - Indicates whether this grade is eligible for a housing advance.
        - Used in housing loan eligibility logic.

    2. per_month_housing_advance (Monetary):
        - Defines the maximum monthly housing advance allowed for employees in this grade.
        - This can be used to compute the installment limits or validate loan caps.

    3. loan_id (Many2one to hr.loan):
        - Links the grade directly to a specific loan record (if needed).
        - This field is optional and can be used to associate a grade-wide loan configuration
          or for analytic/reporting purposes.

    Kaizen Principles Applied:
    - Simplicity: Clean extension of the existing model without code duplication.
    - Reusability: Fields like `per_month_housing_advance` can be reused in loan computation.
    - Maintainability: Keeps loan policy logic modular and centralized per grade.
    - Extensibility: Designed to scale with additional types of allowances or benefits.

    Used In:
    - HR Loan eligibility checks
    - Housing Advance rule enforcement
    - Reporting on grade-based loan limits
    """
    _inherit = 'hr.grade'

    is_housing_advance = fields.Boolean(
        string="Housing Advance",
        help="Enable if employees in this grade are eligible for monthly housing advance.")

    per_month_housing_advance = fields.Monetary(
        string="Per Month Housing Advance",
        currency_field='currency_id',
        help="Maximum monthly housing advance amount applicable for this grade.")

    loan_id = fields.Many2one(
        'hr.loan',
        string="Linked Loan Record",
        help="Optional reference to a specific loan associated with this grade.")
