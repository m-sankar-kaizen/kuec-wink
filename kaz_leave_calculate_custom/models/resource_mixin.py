# -*- coding: utf-8 -*-
from collections import defaultdict
from pytz import utc

from odoo import models
from odoo.addons.resource.models.utils import timezone_datetime


class ResourceMixin(models.AbstractModel):
    _inherit = "resource.mixin"

    def _get_calendar(self, date_from=None):
        """
        Returns the resource calendar used by this resource.

        Priority:
        - resource_calendar_id of the record, if set.
        - company resource calendar as fallback.

        :param date_from: Optional datetime parameter for calendar determination (currently unused).
        :return: resource.calendar record
        """
        self.ensure_one()
        return self.resource_calendar_id or self.company_id.resource_calendar_id

    def _get_work_days_data_batch(self, from_datetime, to_datetime, compute_leaves=True, calendar=None, domain=None,
                                  day_calculation_type=None):
        """
        Compute working time over a period for multiple records efficiently.

        - Uses resource calendar by default or a provided one.
        - Optionally considers leaves during calculation using the `compute_leaves` flag.
        - The `domain` filters leave/time-off records to exclude from working time.
          Default is [('time_type', '=', 'leave')].
        - `day_calculation_type` modifies day counting logic, e.g., calendar days vs working days.

        :param from_datetime: Start datetime (aware or naive; will be converted to UTC).
        :param to_datetime: End datetime (aware or naive; will be converted to UTC).
        :param compute_leaves: If True, excludes leave intervals from working time.
        :param calendar: Optional resource.calendar to use instead of record's calendar.
        :param domain: Domain for identifying leave intervals (None for default).
        :param day_calculation_type: Optional type of day calculation to use.
        :return: dict mapping record id to dict {'days': float, 'hours': float} representing work time.
        """
        resources = self.mapped('resource_id')
        mapped_employees = {e.resource_id.id: e.id for e in self}
        result = {}

        # Convert naive datetime to explicit UTC datetime to avoid timezone issues.
        from_datetime = timezone_datetime(from_datetime)
        to_datetime = timezone_datetime(to_datetime)

        # Group records by calendar, combining resources for batch processing.
        mapped_resources = defaultdict(lambda: self.env['resource.resource'])
        for record in self:
            mapped_resources[calendar or record._get_calendar(from_datetime)] |= record.resource_id

        for calendar, calendar_resources in mapped_resources.items():
            if not calendar:
                # If no calendar, no work time.
                for calendar_resource in calendar_resources:
                    result[calendar_resource.id] = {'days': 0, 'hours': 0}
                continue
            # Compute intervals of work time or attendance with or without leaves considered.
            if compute_leaves:
                intervals = calendar.with_context({'day_calculation_type': day_calculation_type})._work_intervals_batch(
                    from_datetime, to_datetime, calendar_resources, domain)
            else:
                intervals = calendar._attendance_intervals_batch(from_datetime, to_datetime, calendar_resources)

            # Compute working days and hours per resource from intervals.
            for calendar_resource in calendar_resources:
                result[calendar_resource.id] = calendar._get_attendance_intervals_days_data(
                    intervals[calendar_resource.id])

        # Map back from resource ids to original record ids.
        return {mapped_employees[r.id]: result[r.id] for r in resources}

    def list_work_time_per_day(self, from_datetime, to_datetime, calendar=None, domain=None, day_calculation_type=None):
        """
        Return daily work durations for the record's resource within the given period.

        - By default uses the resource calendar but can be overridden.
        - Optionally excludes leaves based on `domain` filter.
        - Returns a sorted list of tuples `(date, hours)` for days with attendance.

        :param from_datetime: Start datetime (aware or naive; converted to UTC).
        :param to_datetime: End datetime (aware or naive; converted to UTC).
        :param calendar: Optional resource.calendar to override default.
        :param domain: Domain filter to identify leaves (None defaults to leave time_type).
        :param day_calculation_type: Optional mode for day calculation logic.
        :return: List of tuples (date, float hours) sorted by date.
        """
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id or self.company_id.resource_calendar_id

        # Ensure datetimes are timezone-aware in UTC.
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)

        compute_leaves = self.env.context.get('compute_leaves', True)
        intervals = calendar.with_context({'day_calculation_type': day_calculation_type})._work_intervals_batch(
            from_datetime, to_datetime, resource, domain, compute_leaves=compute_leaves)[resource.id]

        result = defaultdict(float)
        for start, stop, meta in intervals:
            # Sum total hours worked per date.
            result[start.date()] += (stop - start).total_seconds() / 3600

        return sorted(result.items())
