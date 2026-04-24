from odoo import models, fields
from datetime import datetime, time

DEFAULT_HOURS_PER_DAY = 8.0  # fallback


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """
        We call the original implementation to build the default worked-days lines,
        then replace any leave-related lines with calendar-day based lines for
        leaves where holiday_status_id.day_calculation_type == 'calendar_days'.
        """
        self.ensure_one()
        # call original implementation (super)
        res = super()._get_worked_day_lines(domain=domain, check_out_of_contract=check_out_of_contract)

        # we only do this per single payslip (calling code loops over valid slips)
        # so guard early
        if not self.employee_id or not self.date_from or not self.date_to:
            return res
        # Collect validated leaves overlapping payslip with day_calculation_type == 'calendar_days'
        Leave = self.env['hr.leave']
        # convert payslip dates to datetimes for comparison
        payslip_start_dt = datetime.combine(fields.Date.from_string(self.date_from), time.min)
        payslip_end_dt = datetime.combine(fields.Date.from_string(self.date_to), time.max)

        leave_domain = [
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', payslip_end_dt),
            ('date_to', '>=', payslip_start_dt),
            ('holiday_status_id.day_calculation_type', '=', 'calendar_days'),
        ]
        calendar_leaves = Leave.search(leave_domain)
        if not calendar_leaves:
            return res

        # Remove existing leave-type lines from res (we will rebuild them)
        WorkEntryType = self.env['hr.work.entry.type']
        non_leave_lines = []
        for vals in res:
            # If there is a work_entry_type_id, check its is_leave flag
            wet_id = vals.get('work_entry_type_id')
            if not wet_id:
                non_leave_lines.append(vals)
            else:
                wet = WorkEntryType.browse(wet_id)
                if not wet.is_leave:
                    non_leave_lines.append(vals)
                # else: skip leave lines (we will compute calendar-days lines)

        # Build new leave lines from calendar_leaves
        new_leave_lines = []
        contract_calendar = self.contract_id.resource_calendar_id if self.contract_id else None

        for leave in calendar_leaves:
            # compute overlap with payslip (calendar days)
            leave_start = leave.date_from.date()
            leave_end = leave.date_to.date()
            payslip_start = fields.Date.from_string(self.date_from)
            payslip_end = fields.Date.from_string(self.date_to)

            # overlap interval
            start = max(leave_start, payslip_start)
            stop = min(leave_end, payslip_end)
            # inclusive days
            overlap_days = (stop - start).days + 1
            if overlap_days <= 0:
                continue

            # handle half-day request
            if getattr(leave, 'request_unit_half', False):
                days = 0.5
                # compute full day hours by looking at the start date (or fallback)
                full_day_hours = DEFAULT_HOURS_PER_DAY
                try:
                    if contract_calendar:
                        dt = datetime.combine(start, time.min)
                        full_day_hours = contract_calendar.get_work_hours_count(
                            datetime.combine(start, time.min),
                            datetime.combine(start, time.max),
                            compute_leaves=False
                        ) or full_day_hours
                except Exception:
                    full_day_hours = DEFAULT_HOURS_PER_DAY
                hours = full_day_hours / 2.0
            else:
                days = float(overlap_days)
                # compute full-day hours (try contract calendar for representative day)
                try:
                    if contract_calendar:
                        # choose the first overlapping day to get full-day hours count
                        full_day_hours = contract_calendar.get_work_hours_count(
                            datetime.combine(start, time.min),
                            datetime.combine(start, time.max),
                            compute_leaves=False
                        )
                        if not full_day_hours:
                            full_day_hours = DEFAULT_HOURS_PER_DAY
                    else:
                        full_day_hours = DEFAULT_HOURS_PER_DAY
                except Exception:
                    full_day_hours = DEFAULT_HOURS_PER_DAY

                hours = days * full_day_hours

            # resolve work_entry_type for this leave (try leave-specific WET, then fallback to a leave-type work entry)
            wet = leave.holiday_status_id.work_entry_type_id
            if not wet:
                # fallback: pick any is_leave work_entry_type
                wet = WorkEntryType.search([('is_leave', '=', True)], limit=1)

            # if still not found, skip this leave
            if not wet:
                continue

            new_leave_lines.append({
                'sequence': wet.sequence or 999,
                'work_entry_type_id': wet.id,
                'number_of_days': days,
                'number_of_hours': hours,
            })

        # Merge: keep non-leave lines and append new leave lines, then sort by sequence so payroll ordering preserved
        merged = non_leave_lines + new_leave_lines
        merged_sorted = sorted(merged, key=lambda x: x.get('sequence', 999))

        return merged_sorted
