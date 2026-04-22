import itertools
from collections import defaultdict
from datetime import datetime
from dateutil.rrule import rrule, DAILY
from pytz import timezone, utc

from odoo.addons.resource.models.resource import float_to_time
from odoo import models
from odoo.osv import expression
from odoo.addons.hr_work_entry_contract.models.hr_work_intervals import WorkIntervals
from odoo.tools import float_round


class ResourceCalendar(models.Model):
    """
        Extends the standard Odoo resource.calendar model to provide
        advanced attendance interval calculations that consider resource-specific
        calendars, time zones, two-week calendar patterns, and working days vs
        calendar days logic.

        Key functionalities added:
        --------------------------
        - Calculation of attendance intervals broken down by days and hours
          (_get_attendance_intervals_days_data)
        - Batch retrieval of attendance intervals for multiple resources over
          a datetime range, localized by timezone and filtered by day calculation
          type context (_attendance_intervals_batch)

        This extension supports:
        - Two-week repeating calendar schedules
        - Resource-specific and generic calendar attendances
        - Correct localization and clipping of attendance intervals to resource
          timezones and requested date ranges
        - Handling of lunch periods as a filter
        - Differentiation of day calculation types, e.g., 'working_days' vs
          'calendar_days' as passed in context

        Intended for use in HR and workforce management modules requiring precise
        work attendance and leave calculations.

        Usage:
        ------
        This model is typically called internally by HR and attendance modules to
        gather working intervals for employees/resources based on their assigned
        calendars, enabling accurate leave and work entry computations.

        Author: Your Company / Contributor
        Date: July 2025
        """

    _inherit = 'resource.calendar'

    # --------------------------------------------------
    # Private Methods / Helpers
    # --------------------------------------------------

    def _get_attendance_intervals_days_data(self, attendance_intervals):
        """
        Calculate the total leave duration expressed in days and hours
        for the given attendance intervals.

        Each interval is a tuple of (start_datetime, stop_datetime, attendance_records),
        where attendance_records is a recordset of 'resource.calendar.attendance'.

        The method computes:
          - The sum of hours covered by the intervals
          - The equivalent days weighted by the attendance durations,
            accounting proportionally for partial coverage of intervals.

        Returns a dictionary with keys:
          - 'days': total days rounded to 0.001 precision (closest 1/16 day)
          - 'hours': total hours as float

        Args:
            attendance_intervals (list of tuples): Each tuple contains
                (start_datetime, stop_datetime, attendance_records)

        Returns:
            dict: {'days': float, 'hours': float}
        """
        day_hours = defaultdict(float)
        day_days = defaultdict(float)

        for start, stop, meta in attendance_intervals:
            # Calculate interval length in hours
            interval_hours = (stop - start).total_seconds() / 3600

            # Aggregate hours by day
            day_hours[start.date()] += interval_hours

            # Proportionally calculate days covered by attendance
            total_duration_hours = sum(meta.mapped('duration_hours'))
            total_duration_days = sum(meta.mapped('duration_days'))
            if total_duration_hours > 0:
                day_days[start.date()] += total_duration_days * interval_hours / total_duration_hours

        return {
            # Round total days to nearest 0.001 (1/16 day approx)
            'days': float_round(sum(day_days[day] for day in day_days), precision_rounding=0.001),
            'hours': sum(day_hours.values()),
        }

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, lunch=False):
        """
        Compute attendance intervals for a batch of resources over a datetime range.

        It returns a dictionary keyed by resource ID, each containing WorkIntervals
        representing the resource's attendance within the specified period.

        The calculation considers:
          - Resource-specific attendances
          - Calendar attendances (general)
          - Timezones of resources (localized intervals)
          - Working days or calendar days logic, influenced by context key
            'day_calculation_type'. If 'working_days', filters work entry types to 'WORK100'.

        Args:
            start_dt (datetime): Start datetime with tzinfo
            end_dt (datetime): End datetime with tzinfo
            resources (recordset or list, optional): Resources to consider.
                If None, default resource resource record is used.
            domain (list of tuples, optional): Additional search domain for attendances.
            tz (pytz timezone, optional): Timezone to localize intervals, defaults to resource tz.
            lunch (bool): Whether to filter attendances for lunch period

        Returns:
            dict: {resource_id: WorkIntervals} containing attendance intervals per resource.
        """
        assert start_dt.tzinfo and end_dt.tzinfo, "start_dt and end_dt must be timezone-aware"
        self.ensure_one()

        # Prepare resource list and IDs
        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]
        resource_ids = [r.id for r in resources_list]

        # Build domain to search attendances
        domain = domain if domain is not None else []
        domain = expression.AND([
            domain,
            [
                ('calendar_id', '=', self.id),
                ('resource_id', 'in', resource_ids),
                ('display_type', '=', False),
                ('day_period', '!=' if not lunch else '=', 'lunch'),
            ],
        ])

        # Determine if working days logic should be used
        use_working_days = self.env.context.get('day_calculation_type') == 'working_days'

        # Search attendances matching domain
        attendances = self.env['resource.calendar.attendance'].search(domain)

        if use_working_days:
            # Filter to relevant work entry types for working days calculation
            attendances = attendances.filtered(
                lambda a: not a.work_entry_type_id or a.work_entry_type_id.code == 'WORK100')

        # Group resources by timezone for localized interval calculation
        resources_per_tz = defaultdict(list)
        for resource in resources_list:
            resources_per_tz[tz or timezone((resource or self).tz)].append(resource)

        # Attendance sets indexed by resource and weekday
        attendance_per_resource = defaultdict(lambda: self.env['resource.calendar.attendance'])
        attendances_per_day = [self.env['resource.calendar.attendance']] * 14  # 7 days * 2 weeks
        weekdays = set()

        # Organize attendances into resource-specific and per day of week
        for attendance in attendances:
            if attendance.resource_id:
                attendance_per_resource[attendance.resource_id] |= attendance
            weekday = int(attendance.dayofweek)
            weekdays.add(weekday)
            if self.two_weeks_calendar:
                weektype = int(attendance.week_type)
                attendances_per_day[weekday + 7 * weektype] |= attendance
            else:
                attendances_per_day[weekday] |= attendance
                attendances_per_day[weekday + 7] |= attendance

        # Normalize start and end to UTC
        start_utc = start_dt.astimezone(utc)
        end_utc = end_dt.astimezone(utc)

        # Calculate bounds per timezone
        bounds_per_tz = {
            tz: (start_dt.astimezone(tz), end_dt.astimezone(tz))
            for tz in resources_per_tz.keys()
        }

        # Calculate overall min start and max end across timezones
        for tz_, bounds in bounds_per_tz.items():
            start_utc = min(start_utc, bounds[0].replace(tzinfo=utc))
            end_utc = max(end_utc, bounds[1].replace(tzinfo=utc))

        # Generate all relevant days between start and end, filtered by weekdays
        days = rrule(DAILY, dtstart=start_utc.date(), until=end_utc.date(), byweekday=weekdays)
        ResourceCalendarAttendance = self.env['resource.calendar.attendance']

        base_result = []
        per_resource_result = defaultdict(list)

        for day in days:
            # Determine week type for two week calendars
            week_type = ResourceCalendarAttendance.get_week_type(day)
            attendances_for_day = attendances_per_day[day.weekday() + 7 * week_type]
            for attendance in attendances_for_day:
                # Skip if outside attendance's active dates
                if (attendance.date_from and day.date() < attendance.date_from) or \
                   (attendance.date_to and attendance.date_to < day.date()):
                    continue

                # Build datetime intervals for attendance hours
                day_from = datetime.combine(day, float_to_time(attendance.hour_from))
                day_to = datetime.combine(day, float_to_time(attendance.hour_to))

                if attendance.resource_id:
                    per_resource_result[attendance.resource_id].append((day_from, day_to, attendance))
                else:
                    base_result.append((day_from, day_to, attendance))

        # Localize base intervals for each timezone, clipping by bounds
        result_per_tz = {
            tz: [
                (max(bounds_per_tz[tz][0], tz.localize(val[0])),
                 min(bounds_per_tz[tz][1], tz.localize(val[1])),
                 val[2])
                for val in base_result
            ]
            for tz in resources_per_tz.keys()
        }

        # Build final result per resource ID combining base and resource-specific intervals
        result_per_resource_id = dict()
        for tz, resources in resources_per_tz.items():
            res = result_per_tz[tz]
            res_intervals = WorkIntervals(res)
            for resource in resources:
                if resource in per_resource_result:
                    resource_specific_result = [
                        (max(bounds_per_tz[tz][0], tz.localize(val[0])),
                         min(bounds_per_tz[tz][1], tz.localize(val[1])),
                         val[2])
                        for val in per_resource_result[resource]
                    ]
                    combined_intervals = itertools.chain(res, resource_specific_result)
                    result_per_resource_id[resource.id] = WorkIntervals(combined_intervals)
                else:
                    result_per_resource_id[resource.id] = res_intervals

        return result_per_resource_id
