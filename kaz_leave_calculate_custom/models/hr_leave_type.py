# -*- coding: utf-8 -*-
from odoo import fields, models


class HrLeaveType(models.Model):
    """
    Inherits:
        hr.leave.type (Odoo standard model)

    Purpose:
        Adds a configurable field to select the basis of leave days calculation:
        working days or calendar days.

    Fields:
        day_calculation_type (Selection): Specifies whether leave days are
            counted as working days or calendar days.
            - 'working_days' (default): Counts only working days (excluding weekends, holidays).
            - 'calendar_days': Counts all calendar days regardless of weekends or holidays.

    Usage:
        This field can be used in leave request computations to apply different
        counting logic based on organizational policies.
    """

    _inherit = 'hr.leave.type'

    day_calculation_type = fields.Selection(
        [
            ('working_days', 'Working Days'),
            ('calendar_days', 'Calendar Days'),
        ],
        string='Days Calculation Type',
        default='working_days',
        required=True,
        help="Determines how leave days are calculated: "
             "Working Days excludes weekends and holidays, "
             "Calendar Days includes all days."
    )
