# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResourceCalendarAttendance(models.Model):
    """
    Extends the 'resource.calendar.attendance' model to compute the duration of
    each attendance period both in hours and days, supporting flexible calculation
    based on the attendance time range and the calendar's configured working hours.

    Fields added:
    - duration_hours: Computed float field representing the length of the attendance
      period in hours, ignoring lunch periods.
    - duration_days: Computed float field representing the attendance period in days.
      It is set to 0 for lunch periods, 0.5 for periods shorter than or equal to
      three-quarters of the daily working hours, and 1 for longer periods.
    """

    _inherit = "resource.calendar.attendance"

    duration_hours = fields.Float(
        compute='_compute_duration_hours',
        string='Duration (hours)',
        help="Length of this attendance period in hours, zero for lunch periods."
    )
    duration_days = fields.Float(
        compute='_compute_duration_days',
        string='Duration (days)',
        store=True,
        readonly=False,
        help="Length of this attendance period in days: 0 for lunch, 0.5 if duration "
             "is less or equal to 75% of daily hours, else 1."
    )

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_hours(self):
        """
        Compute the duration_hours field as the difference between hour_to and hour_from.
        Lunch periods are assigned a duration of 0 hours.
        """
        for attendance in self:
            if attendance.day_period == 'lunch':
                attendance.duration_hours = 0
            else:
                attendance.duration_hours = attendance.hour_to - attendance.hour_from

    @api.depends('day_period', 'duration_hours', 'calendar_id.hours_per_day')
    def _compute_duration_days(self):
        """
        Compute the duration_days field based on the duration_hours and the calendar's
        hours_per_day setting.
        - If attendance is lunch period, duration_days = 0.
        - If duration_hours is less than or equal to 75% of calendar hours per day, duration_days = 0.5.
        - Otherwise, duration_days = 1.
        """
        for attendance in self:
            if attendance.day_period == 'lunch':
                attendance.duration_days = 0
            else:
                threshold = attendance.calendar_id.hours_per_day * 3 / 4
                attendance.duration_days = 0.5 if attendance.duration_hours <= threshold else 1
