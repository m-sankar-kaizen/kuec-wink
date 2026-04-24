# -*- coding: utf-8 -*-
from odoo import models, fields


class HrContract(models.Model):
    """
    Extension of the HR Contract model to include bonus calculation
    fields and performance-based evaluation metrics. These fields
    support detailed modeling of HR incentive structures based on:

    - Objective and subjective performance reviews
    - Assignment multipliers
    - Leave penalties
    - Contract duration-based proration
    - HR categories and classification

    This model is typically used in conjunction with payroll rules or
    reports for bonus computation across evaluation cycles such as
    quarterly, bi-annually, or annually.
    """

    _inherit = 'hr.contract'

    # -------------------------------
    # Core performance-based metrics
    # -------------------------------

    pm = fields.Float(
        string='PM',
        help="Primary metric or performance measure (PM) for the employee."
    )

    perf_rate_overall = fields.Float(
        string="PerfRateOverall",
        help="Aggregated overall performance rating. Could be a weighted average."
    )

    perf_rate_comp = fields.Float(
        string="PerfRateComp",
        help="Component-wise performance rating. Evaluates specific performance areas."
    )

    perf_rate_sum = fields.Float(
        string="PerfRateSum",
        help="Sum of all weighted performance metrics. Used in final rating."
    )

    # -------------------------------
    # Reviewer-based performance ratings
    # -------------------------------

    r1 = fields.Float(
        string="R1",
        help="Rating by first reviewer, typically the direct manager."
    )

    r2 = fields.Float(
        string="R2",
        help="Rating by second reviewer, usually department head or HR."
    )

    final_rate = fields.Float(
        string="Final Rate",
        help="Final consolidated rating, used for bonus calculation."
    )

    # -------------------------------
    # Proration and category mapping
    # -------------------------------

    prorate = fields.Float(
        string='Prorata',
        help="Proration factor applied based on duration of contract or eligibility window."
    )

    category = fields.Char(
        string='Category',
        help="Performance category (e.g., A, B, C) used for classification."
    )

    crdpms = fields.Float(
        string='CPDPMS',
        help="Composite score combining PM and Category for weighted evaluation."
    )

    r_miss_match = fields.Float(
        string='RMissmatch',
        help="Difference or mismatch score between reviewers; may affect trust factor."
    )

    # -------------------------------
    # Adjustment multipliers
    # -------------------------------

    bonus_criteria = fields.Float(
        string='Bonus Criteria (BS)',
        help="Base value from which bonus is derived (usually basic salary)."
    )

    assignment_multiplier = fields.Float(
        string='Assignment Multiplier',
        help="Multiplier to adjust for project importance or complexity."
    )

    excessive_leaves = fields.Integer(
        string='Excessive Leaves',
        help="Number of excessive or unapproved leave days taken in the evaluation period."
    )

    excessive_leaves_multiplier = fields.Float(
        string='Excessive Leaves Multiplier',
        help="Penalty multiplier applied when excessive leaves are present."
    )

    # -------------------------------
    # Bonus outcome values
    # -------------------------------

    total_amount = fields.Float(
        string='Total Amount (AED)',
        help="Final bonus amount before any proration or penalty."
    )

    total_prorated = fields.Float(
        string='Total Prorated',
        help="Bonus amount after applying contract-based proration."
    )

    total_adjusted = fields.Float(
        string='Total Adjusted',
        help="Bonus after applying penalties and multipliers."
    )

    total_pr_adjusted = fields.Float(
        string='Total PR Adjusted',
        help="Final bonus value after both adjustments and proration are factored."
    )
