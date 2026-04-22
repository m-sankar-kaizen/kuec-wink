# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrAttendance(models.Model):
    """
    Inherits the 'hr.attendance' model to add computed 'worked_hours'.

    This enhancement introduces a computed field `worked_hours` that calculates
    the number of hours an employee has worked between their check-in and check-out times.

    The computation is automatically triggered whenever the `check_in` or `check_out` fields are modified.
    """
    _inherit = 'hr.attendance'

    worked_hours = fields.Float(string="Worked Hours",
                                compute="_get_worked_hours",
                                store=True)

    @api.depends('check_in', 'check_out')
    def _get_worked_hours(self):
        """
            Compute method for the 'worked_hours' field.

            Calculates the total worked hours based on the time difference
            between 'check_in' and 'check_out'. The result is stored in hours
            (floating-point value).

            This method will only compute the value if both 'check_in' and
            'check_out' are set.
        """

        for attendance in self:
            if attendance.check_in and attendance.check_out:
                attendance.worked_hours = (attendance.check_out - attendance.check_in).total_seconds() / 3600
