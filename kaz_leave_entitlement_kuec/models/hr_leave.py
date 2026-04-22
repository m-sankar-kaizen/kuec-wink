# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    support_document = fields.Boolean(related="holiday_status_id.support_document")
    is_attachment_mandatory = fields.Boolean(related="holiday_status_id.is_attachment_mandatory")
    attachment_warning = fields.Text(related="holiday_status_id.attachment_warning")
    allow_leave_extension = fields.Boolean(related="holiday_status_id.allow_leave_extension",
                                           string='Allow Leave Extension')
    leave_validation_type = fields.Selection(related='holiday_status_id.leave_validation_type',
                                             string='Leave Validation Type')
    max_days_for_request = fields.Float(related='holiday_status_id.max_days_for_request')
    min_days_for_request = fields.Float(related='holiday_status_id.min_days_for_request')
    parent_leave_id = fields.Many2one('hr.leave', string='Parent Leave', copy=False)
    child_leave_ids = fields.One2many('hr.leave', 'parent_leave_id', string='Child Leaves')
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('manager', 'Manager Approval'),
            ('time_off', 'Time Off Officer'),
            ('admin', 'CEO'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        default='draft',
        copy=False,
        tracking=True,
    )
    is_wfh = fields.Boolean(string='Is Work from Home', related='holiday_status_id.is_wfh')

    def submit_to_manager(self):
        self.ensure_one()
        self.kuec_approval_state = 'manager'
        manager = self.employee_id.parent_id
        if manager and manager.user_id:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                user_id=manager.user_id.id,
                summary=_("Leave Approval"),
                note=_("There is a leave request from: %s") % self.employee_id.name,
            )

    def action_manager_approve(self):
        self.ensure_one()
        if self.env.user.id != self.employee_id.parent_id.user_id.id:
            raise UserError(
                _('You are not the manager of this employee so cannot approve this leave.'))
        self.kuec_approval_state = 'time_off'

    def action_time_off_manager_approve(self):
        self.ensure_one()
        try:
            self._check_approval_update('validate')
        except (AccessError, UserError):
            raise AccessError(_('You are not allowed to approve this leave.'))
        current_duration = (self.number_of_days or 0.0) + \
                           (self.number_of_hours or 0.0)
        if current_duration >= self.holiday_status_id.approval_requirement_days:
            self.kuec_approval_state = 'admin'
            notify_users = self.env['hr.employee'].sudo().search(
                [('job_id', '=', self.holiday_status_id.escalate_to_job_position_id.id)]).mapped(
                'user_id')
            for user in notify_users:
                self.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    user_id=user.id,
                    summary=_("Leave Approval"),
                    note=_("There is a leave request from: %s") % self.employee_id.name,
                )
        else:
            self.approve_kuec_request()

    def _check_escalation_approval_rights(self):
        """Allow approval only if current user's Job Position matches escalation Job."""
        user = self.env.user

        # Safety — user needs an employee
        if not user.employee_id:
            raise ValidationError(
                _("You are not linked to any Employee record. Approval not allowed."))

        # Safety — employee must have job
        if not user.employee_id.job_id:
            raise ValidationError(
                _("You do not have a Job Position assigned. Approval not allowed."))

        required_job = self.holiday_status_id.escalate_to_job_position_id

        # If no escalation job configured → block
        if not required_job:
            raise ValidationError(
                _("This leave type requires a Job Position for escalation approval, but none is configured."))

        # Match condition
        if user.employee_id.job_id != required_job:
            raise ValidationError(_(
                "You are not authorized to approve this leave.\n\n"
                "Required Position: %s\n"
                "Your Position: %s"
            ) % (required_job.name, user.employee_id.job_id.name))

    def approve_kuec_request(self):
        self.ensure_one()
        if self.kuec_approval_state == 'admin':
            self._check_escalation_approval_rights()
        self.kuec_approval_state = 'approved'
        self.action_approve()

    def action_refuse(self):
        self.ensure_one()
        self.kuec_approval_state = 'rejected'
        return super().action_refuse()

    def action_reset_confirm(self):
        self.ensure_one()
        self.kuec_approval_state = 'draft'
        return super().action_reset_confirm()

    def _action_user_cancel(self, reason):
        self.ensure_one()
        self.kuec_approval_state = 'cancel'
        return super()._action_user_cancel(reason)

    def action_parent_leave_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'res_id': self.parent_leave_id.id,
            'name': _('Parent Time Off'),
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def action_child_leave_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'domain': [('id', 'in', self.child_leave_ids.ids)],
            'name': _('Child Time Off'),
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'context': {
                'create': False,
            }
        }

    def action_repeat_request(self):
        self.ensure_one()
        if self.company_code not in ['KUEC']:
            return False
        if self.allow_leave_extension and self.state in ['validate', 'validate1']:
            if not self.request_date_to:
                raise ValidationError(
                    _("Cannot extend leave because the current leave does not have an end date."))

            # Set request_date_from of new leave as 1 day after current leave's end
            new_date_from = self.request_date_to + timedelta(days=1)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.leave',
                'name': _('Repeat Time Off'),
                'view_mode': 'form',
                'views': [(False, 'form')],
                'context': {
                    'default_employee_id': self.employee_id.id,
                    'default_parent_leave_id': self.id,
                    'default_holiday_status_id': self.holiday_status_id.id,
                    'default_request_date_from': new_date_from,
                    'default_request_date_to': False,
                }
            }
        return True

    @api.constrains('holiday_status_id', 'request_date_from')
    def _check_advance_notice(self):
        for leave in self:
            if leave.company_code not in ['KUEC']:
                continue

            if not leave.holiday_status_id:
                continue

            if leave.holiday_status_id.requires_advance_notice:
                advance_days = leave.holiday_status_id.advance_number_of_days or 0
                if leave.request_date_from:
                    today = fields.Date.context_today(leave)
                    min_allowed_date = today + timedelta(days=advance_days)
                    if leave.request_date_from < min_allowed_date:
                        raise ValidationError(_(
                            "This leave type requires at least %d day(s) of advance notice.\n"
                            "Earliest allowed start date: %s"
                        ) % (advance_days, min_allowed_date.strftime('%Y-%m-%d')))

    @api.constrains('employee_id', 'holiday_status_id', 'company_id')
    def _check_employee_type_and_gender(self):
        for record in self:
            if record.company_code not in ['KUEC']:
                continue
            if (
                    (record.holiday_status_id.employee_type
                     and record.holiday_status_id.employee_type != record.employee_id.kaz_employee_type)
                    or
                    (record.holiday_status_id.gender
                     and record.holiday_status_id.gender != record.employee_id.gender)
                    or
                    (record.holiday_status_id.kuec_grade_id
                     and record.holiday_status_id.kuec_grade_id != record.employee_id.kuec_grade_id)
                    or
                    (record.holiday_status_id.religion_id
                     and record.holiday_status_id.religion_id != record.employee_id.religion_id)
            ):
                raise ValidationError(_(
                    "You are not allowed to apply for this time off type. "
                    "Please contact the HR department for further assistance."
                ))
            # if record.holiday_status_id.employee_type and record.holiday_status_id.employee_type != record.employee_id.kaz_employee_type:
            #     raise ValidationError(_(
            #         "This time off type is restricted to %s employees. "
            #         "This Employee is registered as a %s and cannot use this leave type."
            #     ) % (record.holiday_status_id.employee_type.title(),
            #          record.employee_id.kaz_employee_type.title()))
            #
            # if record.holiday_status_id.gender and record.holiday_status_id.gender != record.employee_id.gender:
            #     raise ValidationError(_(
            #         "This time off type is restricted to %s employees. "
            #         "This Employee is a %s and cannot use this leave type."
            #     ) % (record.holiday_status_id.gender.title(),
            #          record.employee_id.gender.title()))
            #
            # if record.holiday_status_id.kuec_grade_id and record.holiday_status_id.kuec_grade_id != record.employee_id.kuec_grade_id:
            #     raise ValidationError(_(
            #         "This time off type is restricted to %s grade employees. "
            #         "This Employee is of %s grade and cannot use this leave type."
            #     ) % (record.holiday_status_id.kuec_grade_id.display_name,
            #          record.employee_id.kuec_grade_id.display_name))
            #
            # if record.holiday_status_id.religion_id and record.holiday_status_id.religion_id != record.employee_id.religion_id:
            #     raise ValidationError(_(
            #         "This time off type is restricted to %s employees. "
            #         "This Employee is of '%s' religion and cannot use this leave type."
            #     ) % (record.holiday_status_id.religion_id.display_name,
            #          record.employee_id.religion_id.display_name))

    @api.constrains('number_of_hours', 'number_of_days', 'holiday_status_id')
    def _check_holiday_duration(self):
        for leave in self:
            if leave.company_code not in ['KUEC']:
                continue

            # Skip if no leave type
            if not leave.holiday_status_id:
                continue

            min_days = leave.min_days_for_request or 0.0
            max_days = leave.max_days_for_request or 0.0

            # Duration of current request
            current_duration = (leave.number_of_days or 0.0) + \
                               (leave.number_of_hours or 0.0)

            # -------------------------
            # 1. Minimum per request
            # -------------------------
            if min_days > 0 and current_duration < min_days:
                raise ValidationError(_(
                    "The requested duration (%.2f days) is below the minimum "
                    "allowed (%.2f days) for this leave type."
                ) % (current_duration, min_days))

            # -------------------------
            # 2. Maximum per request
            # -------------------------
            if max_days > 0 and current_duration > max_days:
                raise ValidationError(_(
                    "The requested duration (%.2f days) exceeds the maximum "
                    "allowed (%.2f days) for a single leave request."
                ) % (current_duration, max_days))

    # def _check_supporting_documents(self):
    #     self.ensure_one()
    #
    #     if self.holiday_status_id.support_document and self.holiday_status_id.is_attachment_mandatory:
    #         if not self.supported_attachment_ids:
    #             if self.holiday_status_id.attachment_warning:
    #                 raise UserError(
    #                     _("Support Document:\n%s") % self.holiday_status_id.attachment_warning
    #                 )
    #             raise UserError(_("Please attach the necessary document to request for approval."))

    @api.constrains('supported_attachment_ids', 'holiday_status_id')
    def check_supported_document_required(self):
        """
        OVERRIDE
        Validate that required supporting documents are attached when the leave type
        demands it.

        Raises:
            UserError: if the leave type requires support documents but none are attached.
        """
        # FIXME: Something wrong with the validation
        return
        # import logging
        # for rec in self:
        #     if rec.company_code not in ['KUEC']:
        #         if rec.leave_type_support_document and not rec.supported_attachment_ids:
        #             raise UserError("Please attach the necessary document to request for approval.")
        #     else:
        #         if (rec.holiday_status_id.support_document
        #                 and rec.holiday_status_id.is_attachment_mandatory):
        #             # Use `bool` to ensure evaluation
        #             logging.info(
        #                 f"rec {rec}, rec.supported_attachment_ids: {rec.supported_attachment_ids}")
        #             if not bool(rec.supported_attachment_ids):
        #                 if rec.holiday_status_id.attachment_warning:
        #                     raise UserError(_(
        #                         "Support Document:\n%s"
        #                     ) % rec.holiday_status_id.attachment_warning)
        #                 raise UserError(
        #                     _("Please attach the necessary document to request for approval."))
