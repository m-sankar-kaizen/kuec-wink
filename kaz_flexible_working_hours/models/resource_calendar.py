# -*- coding: utf-8 -*-
from odoo import models, fields


class ResourceCalendar(models.Model):
    """
    Extends the `resource.calendar` model to include a flexible check-in buffer.

    This extension adds a field `flexible_check_in` which represents the allowed buffer
    time in hours for employees to check in late without being marked as late.

    Field Details:
    --------------
    flexible_check_in : Float
        - Unit: Hours (e.g., 0.5 = 30 minutes)
        - Purpose: Acts as a grace period added to the planned check-in time.
        - Used in `hr.attendance` late check-in logic to compute if an employee
          is actually late or within the allowed buffer.

    Business Use:
    -------------
    Organizations that allow flexible working hours can use this field to set
    acceptable thresholds for employee punctuality per work schedule.
    """
    _inherit = 'resource.calendar'

    flexible_check_in = fields.Float(
        string="Flexible Check-In (Hours)",
        help="Number of hours after planned check-in "
             "that is considered acceptable without "
             "marking the employee as late."
    )
