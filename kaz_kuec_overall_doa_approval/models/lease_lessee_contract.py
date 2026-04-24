# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class LeaseLesseeContract(models.Model):
    _name = 'lease.lessee.contract'
    _inherit = ['lease.lessee.contract', 'approval.base.mixin']

    is_readonly = fields.Boolean(string='Is Readonly')
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('finance_procurement_approval', 'Finance & Procurement Approval'),
            ('approved', 'Fully Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        string="KUEC Approval State",
        default="draft",
        tracking=True,
        copy=False,
    )
    lessee_contract_approval_ids = fields.One2many('lease.lessee.contract.approval',
                                                   'lessee_contract_id',
                                                   string='Approval/Rejection/Return History')

    @property
    def _approval_model(self):
        return 'lease.lessee.contract.approval'

    @property
    def _approval_line(self):
        return self.lessee_contract_approval_ids

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_lessee_contract_id': self.id
        }

    def _get_department_head(self):
        users = self._get_group_users('account.group_account_manager')
        doa_users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_head_department')
        users += doa_users
        users.filtered(lambda rec: rec.company_id.company_code in ['KUEC'])
        return users.mapped('employee_id')

    def action_lock(self):
        self.ensure_one()
        self.is_readonly = True

    def action_unlock(self):
        self.ensure_one()
        self.is_readonly = False

    def submit_for_approval(self):
        users = self._get_department_head().mapped('user_id')
        summary = _('Approval of Lessee Contract'),
        note = _('Please approve the request for Lessee Contract')
        self._perform_action('department_approval', users, summary, note)
        self.action_lock()

    def action_submit(self):
        super().action_submit()
        self.submit_for_approval()

    def action_hod_approval(self):
        self.ensure_one()
        # self._validate_hod() #TODO validate HOD
        if self._context.get('signed', False):
            summary = _("Lessee Contract Request Requires Your Review")
            note = _(
                f"The Lessee Contract Request has been Requested by {self.env.user.display_name} "
                "Please review the submitted Lessee Contract Request and proceed with the next steps."
            )

            users = self._get_group_users(
                'kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
            self._perform_action('finance_procurement_approval', users, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_hod_approval')

    def action_head_fin_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_action('approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_head_fin_approval')

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Lessee Contract Form Rejected")
            note = _(
                f"The Lessee Contract request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Lessee Contract form"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            self.action_cancel()
            return True
        else:
            return self._open_approve_reject_wizard('Reject Lessee Contract', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Lessee Contract Form Returned for Correction")
            note = _(
                f"The Lessee Contract request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Lessee Contract form"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            self.state = 'draft'
            self.action_unlock()
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    def action_reset_to_draft(self):
        super().action_reset_to_draft()
        if self.kuec_approval_state != 'draft':
            self.kuec_approval_state = 'draft'

    def action_cancel(self):
        super().action_cancel()
        if self.kuec_approval_state != 'cancel':
            self.kuec_approval_state = 'cancel'
