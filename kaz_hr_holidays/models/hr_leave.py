# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, _
from odoo.exceptions import ValidationError, UserError


class HrLeave(models.Model):
    """
    Extends the hr.leave model to support a multi-level
     approval workflow for leave requests,
    including HR Director and CEO approval stages.
     This model also enforces validations related
    to overlapping leaves, public holidays, and dynamically
     schedules activities for designated groups.
    """
    _inherit = 'hr.leave'

    cycle_approve = fields.Selection(
        selection=[
            ('hr_director', 'HR director'),
            ('ceo', 'CEO'),
            ('done', 'Done')],
        copy=False,
        default='hr_director',
        string="Approval Stage",
        tracking=True,
        help="Tracks the stage of leave approval workflow."
             " Used when multi-level approval is required."
    )

    access_director = fields.Boolean(
        string='Access Director',
        related='holiday_status_id.by_hr_director',
        copy=False,
        help="Automatically set based on leave type. "
             "Used to determine if this leave requires HR Director approval."
    )

    access_ceo = fields.Boolean(
        string='Validation CEO',
        related='holiday_status_id.by_ceo',
        copy=False,
        help="Automatically set based on leave type. "
             "Used to determine if this leave requires CEO approval."
    )

    def send_notify2_group(self, group_xml_id):
        """
        Utility method to schedule a mail activity for all users in a specific group.

        :param group_xml_id: XML ID of the user group (res.groups) to notify.
        """
        users = self.env.ref(group_xml_id).users
        for user in users:
            self.activity_schedule(
                act_type_xmlid='kaz_hr_holidays.mail_activity_holidays_approve',
                note='Please Approve For This Request',
                user_id=user.id
            )

    def action_validate(self, check_state=True):
        """
        Override of the standard `action_validate` to insert custom approval flow logic.
        This is the entry point of the multi-step approval process. It redirects to director or CEO based on config.
        """
        if self.access_director:
            self.send_notify2_group('kaz_hr_holidays.time_of_hr_director_group')
            self.cycle_approve = 'hr_director'
        elif self.access_ceo:
            self.send_notify2_group('kaz_hr_holidays.time_of_hr_ceo_group')
            self.cycle_approve = 'ceo'
        else:
            self.pre_action_validate()

    def director_approve(self):
        """
        Approves leave at the HR Director level. If CEO approval is required, sends activity to CEO.
        Otherwise, proceeds to final validation.
        """
        if self.access_ceo:
            self.send_notify2_group('kaz_hr_holidays.time_of_hr_ceo_group')
            self.cycle_approve = 'ceo'
        else:
            self.pre_action_validate()

    def ceo_approve(self):
        """
        Final level of approval (CEO). Directly validates the leave.
        """
        self.cycle_approve = 'done'
        self.pre_action_validate()

    def _prepare_employees_holiday_values(self, employees, date_from_tz, date_to_tz):
        self.ensure_one()
        work_days_data = employees._get_work_days_data_batch(date_from_tz, date_to_tz)
        return [{
            'name': self.name,
            'holiday_status_id': self.holiday_status_id.id,
            'date_from': date_from_tz,
            'date_to': date_to_tz,
            'request_date_from': self.date_from,
            'request_date_to': self.date_to,
            'number_of_days': work_days_data[employee.id]['days'],
            'employee_id': employee.id,
            'state': 'validate',
        } for employee in employees if work_days_data[employee.id]['days']]

    def pre_action_validate(self):
        """
        Final validation logic for approved leaves. Handles:
            - Public holiday check
            - Overlapping leave check
            - Leave record splitting for partial conflicts
            - Leave validation routing based on leave type (individual/group)
        """
        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(
                _('The following employees are not supposed to work during that period:\n %s') %
                ','.join(leaves.mapped('employee_id.name'))
            )

        if any(holiday.state not in ['confirm',
                                     'validate1'] and holiday.validation_type != 'no_validation'
               for holiday in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})

        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

            # Group leave validation
            if leave.employee_id:
                employees = leave.employee_id

                # Find conflicting leaves and split them if required
                conflicting_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True
                ).search([
                    ('date_from', '<=', leave.date_to),
                    ('date_to', '>', leave.date_from),
                    ('state', 'not in', ['cancel', 'refuse']),
                    ('employee_id', 'in', employees.ids)
                ])

                if conflicting_leaves:
                    if leave.leave_type_request_unit != 'day' or any(
                            l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                        raise ValidationError(
                            _('You can not have 2 time off that overlaps on the same day.'))

                    target_states = {l.id: l.state for l in conflicting_leaves}
                    conflicting_leaves.action_refuse()

                    split_leaves_vals = []
                    for conflicting_leave in conflicting_leaves:
                        # Split the leave before the new approved leave
                        if conflicting_leave.date_from < leave.date_from:
                            before_leave_vals = conflicting_leave.copy_data({
                                'date_from': conflicting_leave.date_from.date(),
                                'date_to': leave.date_from.date() + timedelta(days=-1),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            before_leave = self.env['hr.leave'].new(before_leave_vals)
                            before_leave._compute_date_from_to()
                            if before_leave.date_from < before_leave.date_to:
                                split_leaves_vals.append(
                                    before_leave._convert_to_write(before_leave._cache))

                        # Split the leave after the new approved leave
                        if conflicting_leave.date_to > leave.date_to:
                            after_leave_vals = conflicting_leave.copy_data({
                                'date_from': leave.date_to.date() + timedelta(days=1),
                                'date_to': conflicting_leave.date_to.date(),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            after_leave = self.env['hr.leave'].new(after_leave_vals)
                            after_leave._compute_date_from_to()
                            if after_leave.date_from < after_leave.date_to:
                                split_leaves_vals.append(
                                    after_leave._convert_to_write(after_leave._cache))

                    split_leaves = self.env['hr.leave'].with_context(
                        tracking_disable=True,
                        mail_activity_automation_skip=True,
                        leave_fast_create=True,
                        leave_skip_state_check=True
                    ).create(split_leaves_vals)
                    split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

                values = leave._prepare_employees_holiday_values(employees, self.date_from, self.date_to)
                leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    no_calendar_sync=True,
                    leave_skip_state_check=True,
                    leave_compute_date_from_to=True,
                ).create(values)

                leaves._validate_leave_request()

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})

        self._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            self.filtered(
                lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True
