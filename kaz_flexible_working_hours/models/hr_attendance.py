# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import models, fields, api


class HrAttendance(models.Model):
    """
    Extension of `hr.attendance` model to support planned working hours and late check-in calculations.

    This extension adds:
    - `planned_check_in` / `planned_check_out`: Computed datetime fields representing the expected
      check-in and check-out times based on the employee's working schedule (`resource.calendar`).
    - `planned_check_in_display` / `planned_check_out_display`: Readable string representations of the planned times.
    - `late_in`: Calculated float value representing how many hours late the employee arrived,
      taking into account the allowed flexible buffer time.

    Business Logic:
    ----------------
    - The planned times are computed from the employee's calendar (`resource.calendar.attendance_ids`)
      by finding the earliest and latest attendance records for the given weekday.
    - The `late_in` value is calculated in decimal hours based on the actual check-in versus
      planned check-in plus buffer.
    """
    _inherit = 'hr.attendance'

    planned_check_in = fields.Datetime(
        string="Planned Check-In",
        compute='_compute_planned_checkin',
        readonly=True,
        help="Expected check-in datetime based on attendance rules."
    )

    planned_check_in_display = fields.Char(
        string="Planned Check-In (Display)",
        compute='_compute_planned_check_in_display',
        help="Formatted version of the planned check-in time for display."
    )

    flexible_check_in = fields.Float(
        string="Flexible Check-in (Hours)",
        related='employee_id.resource_calendar_id.flexible_check_in',
        help="Number of hours of grace time allowed for check-in."
    )

    planned_check_out = fields.Datetime(
        string="Planned Check-Out",
        compute='_compute_planned_checkout',
        store=True,
        readonly=True,
        help="Expected check-out datetime based on attendance rules."
    )

    planned_check_out_display = fields.Char(
        string="Planned Check-Out (Display)",
        compute='_compute_planned_check_out_display',
        help="Formatted version of the planned check-out time for display."
    )

    late_in = fields.Float(
        string="Late Check-in (Hours)",
        compute='_compute_late_checkin',
        readonly=True,
        help="Late duration in hours, considering planned check-in and buffer."
    )

    resource_calendar_id = fields.Many2one(
        related='employee_id.resource_calendar_id')
    hours_per_day = fields.Float(
        related='resource_calendar_id.hours_per_day')

    @api.depends('employee_id', 'check_in',
                 'employee_id.resource_calendar_id',
                 'employee_id.resource_calendar_id.attendance_ids')
    def _compute_planned_checkin(self):
        """
        Compute the expected/planned check-in time from the employee's attendance schedule.

        Logic:
        - Identify the weekday of `check_in`
        - Find the earliest attendance rule for that day
        - Convert the `hour_from` float to an actual naive datetime using the check-in date
        - Store both a datetime (`planned_check_in`)
        """
        for rec in self:
            rec.planned_check_in = False
            if not rec.check_in or not rec.employee_id:
                continue

            weekday = rec.check_in.weekday()
            calendar = rec.employee_id.resource_calendar_id
            attendances = calendar.attendance_ids.filtered(lambda a: a.dayofweek == str(weekday))

            if attendances:
                earliest = min(attendances, key=lambda a: a.hour_from, default=False)
                hours = int(earliest.hour_from)
                minutes = int(round((earliest.hour_from - hours) * 60))
                planned_dt = datetime.combine(rec.check_in.date(), datetime.min.time()).replace(
                    hour=hours, minute=minutes
                )
                rec.planned_check_in = planned_dt

    @api.depends('planned_check_in', 'flexible_check_in')
    def _compute_planned_check_in_display(self):
        """
        Compute a readable version of the planned check-in datetime.
        """
        for rec in self:
            if not rec.planned_check_in:
                rec.planned_check_in_display = ''
                continue

            flexible_delta = timedelta(hours=rec.flexible_check_in or 0)
            new_time = (rec.planned_check_in + flexible_delta).strftime("%H:%M:%S")
            rec.planned_check_in_display = (
                    rec.planned_check_in.strftime("%m/%d/%Y %H:%M:%S") + " - " + new_time
            )

    @api.depends('employee_id', 'check_out',
                 'employee_id.resource_calendar_id',
                 'employee_id.resource_calendar_id.attendance_ids')
    def _compute_planned_checkout(self):
        """
        Compute the expected/planned check-out time from the employee's attendance schedule.

        Logic:
        - Identify the weekday of `check_out`
        - Find the latest attendance rule for that day
        - Convert the `hour_to` float to an actual naive datetime using the check-out date
        - Store both a datetime (`planned_check_out`)
        """
        for rec in self:
            rec.planned_check_out = False
            if not rec.check_out or not rec.employee_id:
                continue

            weekday = rec.check_out.weekday()
            calendar = rec.employee_id.resource_calendar_id
            attendances = calendar.attendance_ids.filtered(lambda a: a.dayofweek == str(weekday))

            if attendances:
                latest = max(attendances, key=lambda a: a.hour_to, default=False)
                hours = int(latest.hour_to)
                minutes = int(round((latest.hour_to - hours) * 60))
                planned_dt = datetime.combine(rec.check_out.date(), datetime.min.time()).replace(
                    hour=hours, minute=minutes
                )
                rec.planned_check_out = planned_dt

    @api.depends('planned_check_out', 'flexible_check_in')
    def _compute_planned_check_out_display(self):
        """
        Compute a human-readable version of the planned check-out time.
        """
        for rec in self:
            if not rec.planned_check_out:
                rec.planned_check_out_display = ''
                continue

            flexible_delta = timedelta(hours=rec.flexible_check_in or 0)
            new_time = (rec.planned_check_out + flexible_delta).strftime("%H:%M:%S")
            rec.planned_check_out_display = (
                    rec.planned_check_out.strftime("%m/%d/%Y %H:%M:%S") + " - " + new_time
            )

    @api.depends('employee_id', 'check_in', 'planned_check_in')
    def _compute_late_checkin(self):
        """
        Calculate the late-in duration in decimal hours.

        Logic:
        - Convert the actual `check_in` time to local time and make it naive
        - Parse the `planned_check_in_display` into a datetime
        - Add buffer time (if any) to the planned check-in
        - Compute the difference in hours if actual check-in exceeds buffered time
        - If employee checked in early or on time (within buffer), result is 0.0
        """
        for rec in self:
            rec.late_in = 0.0
            if rec.check_in and rec.planned_check_in:
                actual_checkin = fields.Datetime.context_timestamp(rec, rec.check_in).replace(
                    tzinfo=None)
                planned_dt = rec.planned_check_in
                # buffer = timedelta(hours=rec.flexible_check_in or 0.0)
                allowed_checkin_time = planned_dt

                if actual_checkin > allowed_checkin_time:
                    delay = actual_checkin - allowed_checkin_time
                    rec.late_in = round(delay.total_seconds() / 3600, 2)
