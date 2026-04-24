# -*- coding: utf-8 -*-
import pytz

from pytz import timezone
from datetime import timedelta

from odoo import models, fields, _, api
from odoo.exceptions import UserError, ValidationError


class HrLeave(models.Model):
    """
    Extension of the 'hr.leave' model to support a three-level time-off approval process.

    Adds:
    - New approval state `validate2` for HR Manager.
    - Field tracking for HR Manager approver.
    - Computed fields to determine visibility and access of three-level approval.
    - Logic to manage first, second, and HR manager approvals.
    """
    _inherit = 'hr.leave'

    state = fields.Selection(selection_add=[
        ('validate2', 'HR Manager'),
        ('validate', 'Validate'), ])
    hr_manager_approver_id = fields.Many2one(
        'hr.employee',
        string='HR Manager Approval',
        readonly=True,
        copy=False,
        help="Employee who approved at the HR Manager level"
    )
    is_three_level = fields.Boolean(
        'Is Three Level',
        compute='_compute_is_approve_three_level',
        help="True if the request requires 3-level approval"
    )
    can_three_level = fields.Boolean(
        'Three Level',
        compute='_compute_can_approve_three_level',
        help="True if current user is HR Manager and can approve"
    )

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_is_approve_three_level(self):
        """Compute whether the leave request is of type three-level."""
        for holiday in self:
            if holiday.validation_type == 'three_level':
                holiday.is_three_level = True
            else:
                holiday.is_three_level = False
            if holiday.state == 'approved':
                holiday.is_three_level = True

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve_three_level(self):
        """Determine if the current user is allowed to approve as HR Manager."""
        is_hr_manager = self.env.user.has_group(
            'kaz_3_level_timeoff_approval.group_hr_manager')
        for holiday in self:
            holiday.can_three_level = (
                    holiday.state == 'validate1' and
                    holiday.validation_type == 'three_level' and
                    is_hr_manager
            )

    def action_approve(self, check_state=True):
        """
        First level approval for leave request.
        Sets state to `validate1` if validation type is 'both' or 'three_level',
        otherwise directly validates the request.
        """
        if check_state and any(holiday.state != 'confirm' for holiday in self):
            raise UserError(
                _('Time off request must be confirmed ("To Approve") in order to approve it.'))

        current_employee = self.env.user.employee_id
        self.filtered(lambda hol: hol.validation_type in ('both', 'three_level')).write(
            {'state': 'validate1', 'first_approver_id': current_employee.id})

        for holiday in self.filtered(lambda holiday: holiday.employee_id.user_id):
            user_tz = timezone(holiday.tz)
            utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
            holiday.message_post(
                body=_('Your %(leave_type)s planned on %(date)s has been accepted',
                       leave_type=holiday.holiday_status_id.display_name,
                       date=utc_tz.replace(tzinfo=None)),
                partner_ids=holiday.employee_id.user_id.partner_id.ids)

        self.filtered(
            lambda hol: hol.validation_type not in ('both', 'three_level')).action_validate()

        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        return True

    def action_hr_manager(self):
        """
        Second level approval for HR Manager.
        Sets state to `validate2` and logs HR Manager approver.
        """
        current_employee = self.env.user.employee_id
        self.filtered(lambda hol: hol.validation_type == 'three_level').write({
            'state': 'validate2',
            'hr_manager_approver_id': current_employee.id
        })

        for holiday in self.filtered(lambda holiday: holiday.employee_id.user_id):
            user_tz = timezone(holiday.tz)
            utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
            holiday.message_post(
                body=_('Your %(leave_type)s planned on %(date)s has been accepted',
                       leave_type=holiday.holiday_status_id.display_name,
                       date=utc_tz.replace(tzinfo=None)),
                partner_ids=holiday.employee_id.user_id.partner_id.ids)

        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        return True

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

    def action_validate(self, check_state=True):
        """
        Inherit action_validate
        :param check_state:
        :return:
        """
        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(_('The following employees are not supposed to work during that period:\n %s') % ','.join(leaves.mapped('employee_id.name')))
        if check_state and any(holiday.state not in ['confirm', 'validate1', 'validate2'] and holiday.validation_type != 'no_validation' for holiday in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})

        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']
        hr_manager_approver_id = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            elif leave.validation_type == 'three_level':
                hr_manager_approver_id += leave
            else:
                leaves_first_approver += leave

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})
        hr_manager_approver_id.write({'hr_manager_approver_id': current_employee.id})

        self._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            self.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True
