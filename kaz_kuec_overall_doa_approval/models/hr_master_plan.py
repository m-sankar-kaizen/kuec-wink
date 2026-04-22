from odoo import models, fields, _, api
from datetime import date, timedelta
from odoo.exceptions import UserError, ValidationError


class HrMasterPlan(models.Model):
    _inherit = 'hr.master.plan'

    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
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
    kuec_shareholder_attachment = fields.Binary(
        string='KUEC Shareholder Attachment')
    hide_board_approval_attachment = fields.Boolean(
        string='Hide Board Approval Attachment',
        compute='_compute_hide_board_approval_attachment'
    )

    @api.depends('kuec_approval_state', 'kuec_board_attachment',)
    def _compute_hide_board_approval_attachment(self):
        for record in self:
            # Hide only if state is not board_approval AND both attachments are empty
            record.hide_board_approval_attachment = (
                    record.kuec_approval_state != 'board_approval' and
                    not record.kuec_board_attachment
            )

    master_plan_approval_ids = fields.One2many(
        'hr.master.plan.approval', 'master_plan_id',
        string="Approval/Rejection/Return History")

    company_code = fields.Selection(related='company_id.company_code',
                                    string='Company Code')

    def _check_company_access(self):
        self.ensure_one()
        return self.company_code in ['KUEC']

    def _get_group_users(self, group_xml_id):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            raise ValidationError(f"The group '{group_xml_id}' does not exist.")
        if not group.users:
            raise ValidationError(f"No users are assigned to the group '{group.name}'.")
        return group.users

    def _perform_action(self, state, user_ids=None, summary=None, note=None):
        self.ensure_one()
        self._mark_activity_done()
        self.kuec_approval_state = state
        if user_ids:
            self.assign_activity(user_ids, summary, note)

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

    def _open_approve_reject_wizard(self, name, request_type, next_action):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'hr.master.plan.approval',
            'views': [(False, 'form')],
            'context': {
                'default_sequence': len(self.master_plan_approval_ids) + 1,
                'default_request_type': request_type,
                'default_parent_state_at_request': self.kuec_approval_state.title(),
                'default_next_action': next_action,
                'default_master_plan_id': self.id
            }
        }

    # Approvals and Reject and RFC

    def action_submit_for_approval(self):
        self.ensure_one()
        self.write({'kuec_approval_state': 'ccoe_approval'})

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._check_company_access():
            if self._context.get('signed', False):
                summary = _("Yearly Manpower Plan Requires Your Review")
                note = _(
                    f"The Yearly Manpower Plan request has been approved by {self.env.user.display_name} (CCEO). "
                    "Please review the submitted Yearly Manpower Plan form and proceed with the next steps."
                )
                users = self._get_group_users(
                    'kaz_procurement_doa_kuec.group_kuec_ceo')
                self._perform_action('ceo_approval', users, summary, note)
                return True
            else:
                return self._open_approve_reject_wizard('Approve', 'approve',
                                                        'action_ccoe_approval')
        return False

    def action_reject_request(self):
        self.ensure_one()
        if self._check_company_access():
            if self._context.get('signed', False):
                summary = _("Yearly Manpower Plan Form Rejected")
                note = _(
                    f"The Yearly Manpower Plan request has been rejected by {self.env.user.display_name}. "
                    "Please review the submitted Yearly Manpower Plan form"
                )
                self._perform_action('rejected', self.create_uid, summary, note)
                self.rejected()
                return True
            else:
                return self._open_approve_reject_wizard('Reject Yearly Manpower Plan', 'reject',
                                                        'action_reject_request')
        return False

    def action_rfc_request(self):
        self.ensure_one()
        if self._check_company_access():
            if self._context.get('signed', False):
                summary = _("Yearly Manpower Plan Returned for Correction")
                note = _(
                    f"The Yearly Manpower Plan request has been Returned for Correction by {self.env.user.display_name}. "
                    "Please review the submitted Yearly Manpower Plan form."
                )
                self._perform_action('draft', self.create_uid, summary, note)
                self.reset_to_draft()
                return True
            else:
                return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                        'action_rfc_request')
        return False

    def action_ceo_approval(self):
        self.ensure_one()
        if self._check_company_access():
            if self._context.get('signed', False):
                self._perform_action('board_approval')
                return True
            else:
                return self._open_approve_reject_wizard('Approve', 'approve',
                                                        'action_ceo_approval')
        return False

    def action_final_approval(self):
            self.ensure_one()
            if self._check_company_access():
                if self._context.get('signed', False):
                    self._perform_action('approved')
                    self.action_active()
                    return True
                else:
                    return self._open_approve_reject_wizard('Approve', 'approve',
                                                            'action_final_approval')
            return False

    def action_board_approval(self):
        self.ensure_one()
        if self._check_company_access():
            if self.kuec_board_attachment:
                return self.action_final_approval()
            else:
                raise ValidationError(_(
                    "Board attachments are required to complete the Yearly Manpower Plan process. "
                    "Please make sure file is attached before proceeding."
                ))
        return False
