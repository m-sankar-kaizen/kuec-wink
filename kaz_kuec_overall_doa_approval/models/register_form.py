# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, _, api
from odoo.exceptions import UserError, ValidationError


class RegisterForm(models.Model):
    _inherit = 'register.form'

    company_code = fields.Selection(related='emp_company_id.company_code', string='Company Code')
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('ceo_approval', 'CEO Approval'),
            ('board_approval', 'KUEC Board Approval'),
            ('approved', 'Fully Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        string="KUEC Approval State",
        default="draft",
        tracking=True,
        copy=False,
    )
    kuec_board_attachment = fields.Binary(string='KUEC Board Attachment')
    kuec_shareholder_attachment = fields.Binary(string='KUEC Shareholder Attachment')
    hide_board_approval_attachment = fields.Boolean(
        string='Hide Board Approval Attachment',
        compute='_compute_hide_board_approval_attachment'
    )

    emp_job_id = fields.Many2one(related='name.job_id', string='Employee Job')
    employee_hod_id = fields.Many2one(related='name.parent_id', string='Department Head')
    register_approval_ids = fields.One2many(
        'register.form.approval', 'register_id',
        string="Approval/Rejection/Return History")

    @api.depends('kuec_approval_state', 'kuec_board_attachment', 'kuec_shareholder_attachment')
    def _compute_hide_board_approval_attachment(self):
        for record in self:
            # Hide only if state is not board_approval AND both attachments are empty
            record.hide_board_approval_attachment = (
                    record.kuec_approval_state != 'board_approval' and
                    not record.kuec_board_attachment and
                    not record.kuec_shareholder_attachment
            )

    def _get_department_head(self):
        return self.employee_hod_id or self.employee_department_id.manager_id

    def _check_company_access(self):
        self.ensure_one()
        return self.company_code in ['KUEC']

    def _is_ceo_employee(self):
        self.ensure_one()
        return self.emp_company_id.ceo_job_id.id == self.emp_job_id.id

    def _validate_hod(self):
        """Validate that the current user is the assigned Department Head.

            Ensures that only the Department Head linked to the employee can
            perform approval actions on the evaluation form.

            Raises:
                UserError: If the current user is not the assigned Department Head.
        """
        self.ensure_one()
        manager = self._get_department_head()
        if manager:
            if manager.user_id:
                if self.env.user != manager.user_id:
                    raise UserError(
                        _("Only the Head of Department assigned to this employee can confirm this request."))
            else:
                raise UserError(_("The Department Head does not have an assigned user."))
        else:
            raise UserError(_("A Department Head is not assigned for this employee."))

    def submit_for_approval(self):
        if self._check_company_access():
            if self._is_ceo_employee():
                users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_board')
                self.kuec_approval_state = 'board_approval'
                summary = _("Please Review The Resignation Form of CEO")
                note = _("Please review and confirm the submitted Resignation Form of CEO.")
                self.assign_activity(users, summary, note)
            else:
                manager = self._get_department_head()
                if not manager:
                    raise UserError(_("A Department Head is not assigned for this employee."))
                if not manager.user_id:
                    raise UserError(_("The Department Head does not have an assigned user."))

                self.kuec_approval_state = 'department_approval'
                summary = _("Please Review The Resignation Form")
                note = _("Please review and confirm the submitted Resignation Form.")
                self.assign_activity(manager.user_id, summary, note)
        return super().submit_for_approval()

    def _open_approve_reject_wizard(self, name, request_type, next_action):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'register.form.approval',
            'views': [(False, 'form')],
            'context': {
                'default_sequence': len(self.register_approval_ids) + 1,
                'default_request_type': request_type,
                'default_parent_state_at_request': self.kuec_approval_state.title(),
                'default_next_action': next_action,
                'default_register_id': self.id
            }
        }

    def _perform_action(self, state, user_ids=None, summary=None, note=None):
        self.ensure_one()
        self._mark_activity_done()
        self.kuec_approval_state = state
        if user_ids:
            self.assign_activity(user_ids, summary, note)

    def _get_group_users(self, group_xml_id):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            raise ValidationError(f"The group '{group_xml_id}' does not exist.")
        if not group.users:
            raise ValidationError(f"No users are assigned to the group '{group.name}'.")
        return group.users

    def action_hod_approval(self):
        self.ensure_one()
        if self._check_company_access():
            self._validate_hod()
            if self._context.get('signed', False):
                summary = _("Resignation Form Requires Your Review")
                note = _(
                    f"The resignation request has been approved by {self.env.user.display_name}. (HOD) "
                    "Please review the submitted resignation form and proceed with the next steps."
                )
                users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_ccoe')
                self._perform_action('ccoe_approval', users, summary, note)
                return True
            else:
                return self._open_approve_reject_wizard('Approve', 'approve',
                                                        'action_hod_approval')
        return False

    def action_board_approval(self):
        self.ensure_one()
        if self._check_company_access():

            if self.kuec_board_attachment and self.kuec_shareholder_attachment:
                return self.action_final_approval()
            else:
                raise ValidationError(_(
                    "Board and Shareholder attachments are required to complete the CEO offboarding process. "
                    "Please make sure both files are attached before proceeding."
                ))
        return False

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._check_company_access():
            if self._context.get('signed', False):
                summary = _("Resignation Form Requires Your Review")
                note = _(
                    f"The resignation request has been approved by {self.env.user.display_name} (CCEO). "
                    "Please review the submitted resignation form and proceed with the next steps."
                )
                users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_ceo')
                self._perform_action('ceo_approval', users, summary, note)
                return True
            else:
                return self._open_approve_reject_wizard('Approve', 'approve',
                                                        'action_ccoe_approval')
        return False

    def action_final_approval(self):
        self.ensure_one()
        if self._check_company_access():
            if self._context.get('signed', False):
                self._perform_action('approved')
                self.approve()
                return True
            else:
                return self._open_approve_reject_wizard('Approve', 'approve',
                                                        'action_final_approval')
        return False

    def action_hod_reject(self):
        self.ensure_one()
        if self._check_company_access():
            self._validate_hod()
            return self.action_reject_request()
        return False

    def action_reject_request(self):
        self.ensure_one()
        if self._check_company_access():
            if self._context.get('signed', False):
                summary = _("Resignation Form Rejected")
                note = _(
                    f"The resignation request has been rejected by {self.env.user.display_name}. "
                    "Please review the submitted resignation form"
                )
                self._perform_action('rejected', self.name.user_id, summary, note)
                self.rejected()
                return True
            else:
                return self._open_approve_reject_wizard('Reject Resignation', 'reject',
                                                        'action_reject_request')
        return False

    def action_hod_rfc(self):
        self.ensure_one()
        if self._check_company_access():
            self._validate_hod()
            return self.action_rfc_request()
        return False

    def action_rfc_request(self):
        self.ensure_one()
        if self._check_company_access():
            if self._context.get('signed', False):
                summary = _("Resignation Form Returned for Correction")
                note = _(
                    f"The resignation request has been Returned for Correction by {self.env.user.display_name}. "
                    "Please review the submitted resignation form"
                )
                self._perform_action('draft', self.name.user_id, summary, note)
                self.reset_to_draft()
                return True
            else:
                return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                        'action_rfc_request')
        return False

    def assign_activity(self, user_ids, summary, note):
        for user in user_ids:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                user_id=user.id,
                summary=summary,
                note=note,
                date_deadline=fields.Date.today() + timedelta(days=3)
            )

    def _mark_activity_done(self, activity_type_xml_id=False):
        """Mark pending activities of a specific type as done."""
        self.ensure_one()
        activity_type_xml_id = activity_type_xml_id or 'mail.mail_activity_data_todo'
        activity_type = self.env.ref(activity_type_xml_id, raise_if_not_found=False)
        if activity_type:
            activities = self.env['mail.activity'].search([
                ('user_id', '=', self.env.user.id),
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done')
            ])
            activities.action_feedback()
