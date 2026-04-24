# -*- coding: utf-8 -*-
from collections import defaultdict
from math import ceil
from datetime import datetime, time

from odoo import api, fields, models
from odoo.addons.resource.models.utils import HOURS_PER_DAY
from odoo.exceptions import UserError


class HrLeave(models.Model):
    """
    Extension of the 'hr.leave' model to enhance leave duration calculations,
    support flexible leave day calculations based on employee contracts,
    resource calendars, and provide validation for required support documents.

    Key Features:
    - Computation of leave duration both in days and hours, respecting
      the employee's resource calendar and working schedule.
    - Support for various leave units (half-day, full day, hours).
    - Dynamically determines the relevant resource calendar based on leave type
      (employee, department, or company).
    - Enforces attachment validation when the leave type requires supporting documents.
    - Accommodates complex contract-based calendar determination, including overlapping contracts.
    """

    _inherit = 'hr.leave'

    day_calculation_type = fields.Selection(
        related='holiday_status_id.day_calculation_type',
        string='Days Calculation Type',
        help='Defines how days should be calculated for this leave type (e.g., calendar days, working days).')

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        """
        Calculate the duration of the leave(s) in days and hours,
        supporting day_calculation_type ('working_days', 'calendar_days', default).
        """
        result = {}
        employee_leaves = self.filtered('employee_id')
        employees_by_dates_calendar = defaultdict(lambda: self.env['hr.employee'])

        for leave in employee_leaves:
            if not leave.date_from or not leave.date_to:
                continue
            employees_by_dates_calendar[
                (leave.date_from, leave.date_to,
                 leave.holiday_status_id.include_public_holidays_in_duration,
                 resource_calendar or leave.resource_calendar_id)
            ] += leave.employee_id

        domain = [
            ('time_type', '=', 'leave'),
            ('company_id', 'in',
             self.env.companies.ids + self.env.context.get('allowed_company_ids', [])),
            '|', ('holiday_id', '=', False), ('holiday_id', 'not in', employee_leaves.ids)
        ]
        for leave in self:
            calendar = resource_calendar or leave.resource_calendar_id
            if not leave.date_from or not leave.date_to or not calendar:
                result[leave.id] = (0, 0)
                continue

            if leave.employee_id:
                if leave.leave_type_request_unit != 'day' and (
                        leave.request_unit_half or leave.request_unit_hours):
                    days = 0
                    hours = 0
                    if leave.request_unit_half:
                        if leave.leave_type_request_unit == 'half_day':
                            days = 0.5
                        else:
                            hours = 4
                    elif leave.request_unit_hours:
                        hours = leave.request_hour_to - leave.request_hour_from
                elif leave.day_calculation_type == 'working_days':
                    work_time_per_day_dict = leave.employee_id._list_work_time_per_day(
                        leave.date_from, leave.date_to,
                        calendar=calendar,
                        domain=domain,
                    )
                    work_time_per_day_list = work_time_per_day_dict.get(leave.employee_id.id, [])
                    days = len(work_time_per_day_list)
                    hours = sum(t[1] for t in work_time_per_day_list)

                elif leave.day_calculation_type == 'calendar_days':
                    hours = calendar.get_work_hours_count(leave.date_from, leave.date_to)
                    days = (leave.date_to.date() - leave.date_from.date()).days + 1

                else:
                    work_days_data = leave.employee_id._get_work_days_data_batch(
                        leave.date_from, leave.date_to,
                        domain=domain,
                        calendar=calendar
                    )[leave.employee_id.id]
                    hours, days = work_days_data['hours'], work_days_data['days']

            else:
                today_hours = calendar.get_work_hours_count(
                    datetime.combine(leave.date_from.date(), time.min),
                    datetime.combine(leave.date_from.date(), time.max),
                    False
                )
                hours = calendar.get_work_hours_count(
                    leave.date_from, leave.date_to,
                    compute_leaves=not leave.holiday_status_id.include_public_holidays_in_duration
                )
                days = hours / (today_hours or HOURS_PER_DAY)

            if leave.leave_type_request_unit == 'day' and check_leave_type:
                days = ceil(days)

            result[leave.id] = (days, hours)

        return result

    @api.constrains('supported_attachment_ids')
    def check_supported_document_required(self):
        """
        Validate that required supporting documents are attached when the leave type
        demands it.

        Raises:
            UserError: if the leave type requires support documents but none are attached.
        """
        for rec in self:
            if rec.leave_type_support_document and not rec.supported_attachment_ids:
                raise UserError("Please attach the necessary document to request for approval.")
