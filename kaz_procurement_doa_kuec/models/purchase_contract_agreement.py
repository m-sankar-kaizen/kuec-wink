# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class PurchaseContractAgreement(models.Model):
    _name = 'purchase.contract.agreement'
    _inherit = ['purchase.contract.agreement', 'approval.base.mixin']

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('finance_procurement_approval', 'Finance & Procurement Approval'),
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
    purchase_contract_approval_ids = fields.One2many(
        'purchase.contract.agreement.approval', 'agreement_id',
        string="Approval/Rejection/Return History")

    is_readonly = fields.Boolean(string='Is Readonly', copy=False)
    kuec_board_attachment = fields.Binary(string='KUEC Board Attachment', copy=False)
    hide_board_approval_attachment = fields.Boolean(
        string='Hide Board Approval Attachment',
        compute='_compute_hide_board_approval_attachment'
    )

    def _check_company_access(self):
        return self.company_code in ['KUEC']

    @property
    def _approval_model(self):
        return 'purchase.contract.agreement.approval'

    @property
    def _approval_line(self):
        return self.purchase_contract_approval_ids

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_agreement_id': self.id
        }

    def action_lock_record(self):
        self.ensure_one()
        self.is_readonly = True

    def action_unlock_record(self):
        self.ensure_one()
        self.is_readonly = False

    def _get_department_head(self):
        self.ensure_one()
        employee = self.create_uid.employee_id
        if not employee:
            raise ValidationError(
                _("No Employee found. Please create an employee for this user")
            )
        manager = employee.parent_id
        if not manager:
            raise ValidationError(
                _("No department head found. Please assign a manager to the employee’s department.")
            )
        if not manager.user_id:
            raise ValidationError(
                _("The department head does not have a linked user. Please configure a user for the manager.")
            )
        return manager

    def _perform_common_action(self, state, group_xml_id):
        summary = _("Contract Agreement Request Requires Your Review")
        note = _(
            f"The Contract Agreement Request has been approved by {self.env.user.display_name} "
            "Please review the submitted Contract Agreement Request form and proceed with the next steps."
        )
        users = self._get_group_users(group_xml_id)
        self._perform_action(state, users, summary, note)

    def submit_to_approve(self):
        if self._check_company_access():
            self.action_lock_record()
            self.kuec_approval_state = 'department_approval'
            summary = _("Contract Agreement Request Requires Your Review")
            note = _(
                f"The Contract Agreement Request has been Requested by {self.env.user.display_name} "
                "Please review the submitted Contract Agreement Request form and proceed with the next steps."
            )
            manager = self._get_department_head()
            self._perform_action('department_approval', manager.user_id, summary, note)
        return super().submit_to_approve()

    def action_hod_reject(self):
        self.ensure_one()
        self._validate_hod()
        return self.action_reject_request()

    def action_hod_rfc(self):
        self.ensure_one()
        self._validate_hod()
        return self.action_rfc_request()

    def action_hod_approval(self):
        self.ensure_one()
        self._validate_hod()
        if self._context.get('signed', False):
            self._perform_common_action('finance_procurement_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_hod_approval')

    def action_head_fin_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.total_amount <= 500_000:
                self._perform_action('approved')
            else:
                self._perform_common_action('ccoe_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_ccoe')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_head_fin_approval')

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.total_amount <= 3_000_000:
                self._perform_action('approved')
            else:
                self._perform_common_action('ceo_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_ceo')
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ccoe_approval')

    def action_ceo_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            if self.total_amount <= 10_000_000:
                self._perform_action('approved')
            else:
                self._perform_common_action('board_approval',
                                            'kaz_procurement_doa_kuec.group_kuec_board')
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ceo_approval')

    def action_board_approval(self):
        self.ensure_one()
        if self.kuec_approval_state == 'board_approval' and not self.kuec_board_attachment:
            raise ValidationError(
                _("Please upload the required Board Approval attachment before proceeding. If the record is locked, unlock it first and upload the attachment.")
            )
        if self._context.get('signed', False):
            self._perform_action('approved')
            self.action_lock_record()
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_board_approval')

    @api.depends('kuec_approval_state', 'kuec_board_attachment')
    def _compute_hide_board_approval_attachment(self):
        for record in self:
            # Hide only if state is not board_approval AND both attachments are empty
            record.hide_board_approval_attachment = (
                    record.kuec_approval_state != 'board_approval' and
                    not record.kuec_board_attachment
            )

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Contract Agreement Request Rejected")
            note = _(
                f"The Contract Agreement Request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Contract Agreement Request"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            self.state = 'rejected'
            return True
        else:
            return self._open_approve_reject_wizard('Reject Contract Agreement', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Contract Agreement Request Returned for Correction")
            note = _(
                f"The Contract Agreement Request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Contract Agreement Request form"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            self.state = 'draft'
            self.action_unlock_record()
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    def action_reject(self):
        res = super().action_cancel()
        self.kuec_approval_state = 'rejected'
        return res


