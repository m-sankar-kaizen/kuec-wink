# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, _, api, fields
from odoo.exceptions import ValidationError, UserError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
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
    is_readonly = fields.Boolean(string='Is Readonly')
    kuec_board_attachment = fields.Binary(string='KUEC Board Attachment')
    kuec_shareholder_attachment = fields.Binary(string='KUEC Shareholder Attachment')
    hide_board_approval_attachment = fields.Boolean(
        string='Hide Board Approval Attachment',
        compute='_compute_hide_board_approval_attachment'
    )
    is_approval_stage = fields.Boolean(related="stage_id.is_approval_stage")
    applicant_approval_ids = fields.One2many(
        'hr.applicant.approval', 'applicant_id',
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

    def _is_ceo_job(self):
        self.ensure_one()
        return self.company_id.ceo_job_id.id == self.job_id.id

    def _get_department_head(self):
        return self.job_id.department_id.manager_id

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

    def assign_activity(self, user_ids, summary, note):
        for user in user_ids:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                user_id=user.id,
                summary=summary,
                note=note,
                date_deadline=fields.Date.today() + timedelta(days=3)
            )

    def _get_group_users(self, group_xml_id):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            raise ValidationError(f"The group '{group_xml_id}' does not exist.")
        if not group.users:
            raise ValidationError(f"No users are assigned to the group '{group.name}'.")
        return group.users

    def action_lock(self):
        self.is_readonly = True

    def action_unlock(self):
        self.is_readonly = False

    def submit_for_approval(self):
        if self._check_company_access():
            self.action_lock()
            if self._is_ceo_job():
                users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_board')
                self.kuec_approval_state = 'board_approval'
                summary = _("Please Review The Recruitment Form of CEO")
                note = _("Please review and confirm the submitted Recruitment Form for CEO.")
                self.assign_activity(users, summary, note)
            else:
                manager = self._get_department_head()
                if not manager:
                    raise UserError(_("A Department Head is not assigned for this employee."))
                if not manager.user_id:
                    raise UserError(_("The Department Head does not have an assigned user."))

                self.kuec_approval_state = 'department_approval'
                summary = _("Please Review The Recruitment Form")
                note = _("Please review and confirm the submitted Recruitment Form.")
                self.assign_activity(manager.user_id, summary, note)

    def _mark_activity_done(self, activity_type_xml_id=False):
        """Mark pending activities of a specific type as done."""
        self.ensure_one()
        activity_type_xml_id = activity_type_xml_id or 'mail.mail_activity_data_todo'
        activity_type = self.env.ref(activity_type_xml_id, raise_if_not_found=False)
        if activity_type:
            activities = self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done')
            ])
            activities.action_feedback()

    def _perform_action(self, state, user_ids=None, summary=None, note=None):
        self.ensure_one()
        self._mark_activity_done()
        self.kuec_approval_state = state
        if user_ids:
            self.assign_activity(user_ids, summary, note)

    def _open_approve_reject_wizard(self, name, request_type, next_action):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'hr.applicant.approval',
            'views': [(False, 'form')],
            'context': {
                'default_sequence': len(self.applicant_approval_ids) + 1,
                'default_request_type': request_type,
                'default_parent_state_at_request': self.kuec_approval_state.title(),
                'default_next_action': next_action,
                'default_applicant_id': self.id
            }
        }

    def action_hod_approval(self):
        self.ensure_one()
        if self._check_company_access():
            self._validate_hod()
            if self._context.get('signed', False):
                summary = _("Recruitment Form Requires Your Review")
                note = _(
                    f"The Recruitment Form has been approved by {self.env.user.display_name}. (HOD) "
                    "Please review the submitted Recruitment form and proceed with the next steps."
                )
                users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_ccoe')
                self._perform_action('ccoe_approval', users, summary, note)
                return True
            else:
                return self._open_approve_reject_wizard('Approve', 'approve',
                                                        'action_hod_approval')
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
                return self.archive_applicant()  # TODO
            else:
                return self._open_approve_reject_wizard('Reject Recruitment', 'reject',
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
                summary = _("Recruitment Form Returned for Correction")
                note = _(
                    f"The recruitment form has been Returned for Correction by {self.env.user.display_name}. "
                    "Please review the submitted recruitment form"
                )
                self._perform_action('draft', self.user_id, summary, note)
                self.active = True
                self.reset_applicant()
                self.action_unlock()
                return True
            else:
                return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                        'action_rfc_request')
        return False

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._check_company_access():
            if self._context.get('signed', False):
                summary = _("Recruitment Form Requires Your Review")
                note = _(
                    f"The recruitment form has been approved by {self.env.user.display_name} (CCEO). "
                    "Please review the submitted recruitment form and proceed with the next steps."
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
            stage = self.env['hr.recruitment.stage'].search([('hired_stage', '=', True)], limit=1)
            if not stage:
                raise ValidationError(_(
                    "No 'Hired Stage' has been configured in Recruitment Stages.\n\n"
                    "Please configure one stage as the Hired Stage before approving "
                    "the applicant."
                ))
            if self._context.get('signed', False):
                self._perform_action('approved')
                self.with_context(skip_validation=True).write({
                    'stage_id': stage.id
                })
                return True
            else:
                return self._open_approve_reject_wizard('Approve', 'approve',
                                                        'action_final_approval')
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

    def toggle_active(self):
        self.kuec_approval_state = 'draft'
        return super().toggle_active()

    def _check_company_access(self):
        self.ensure_one()
        return self.company_code in ['KUEC']

    def write(self, vals):
        stage_id = vals.get('stage_id')
        skip_validation = self._context.get('skip_validation', False)
        if stage_id and self._check_company_access() and not skip_validation:
            if self.kuec_approval_state == 'approved':
                raise ValidationError(_(
                    "This record is approved. You cannot change the stage of an approved applicant."
                ))
            if self.kuec_approval_state not in ['draft', 'rejected', 'cancel']:
                raise ValidationError(_(
                    "This record is pending approval. You cannot change the stage during the approval process."
                ))
            stage = self.env['hr.recruitment.stage'].sudo().browse(stage_id)
            if stage.hired_stage:
                approval_stage = self.env['hr.recruitment.stage'].sudo().search(
                    [('is_approval_stage', '=', True)])
                raise ValidationError(_(
                    "You cannot move the applicant directly to the 'Hired' stage. "
                    "As per company policy, this stage requires approval. "
                    f"Please move the applicant to the stage '{approval_stage.name}' and submit an approval request."
                ))
        return super().write(vals)
