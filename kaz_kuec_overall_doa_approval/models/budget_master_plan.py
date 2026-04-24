# -*- coding: utf-8 -*-
from odoo import models, fields, _


class BudgetMasterPlan(models.Model):
    _name = 'budget.master.plan'
    _inherit = ["budget.master.plan", "approval.base.mixin"]

    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('finance_procurement_approval', 'Finance & Procurement Approval'),
            ('coe_approval', 'COE Approval'),
            ('ceo_approval', 'CEO Approval'),
            ('approved', 'Fully Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled'),
        ],
        string="KUEC Approval State",
        default="draft",
        tracking=True,
        copy=False,
    )
    is_readonly = fields.Boolean(string='Is Readonly', copy=False)
    master_plan_approval_ids = fields.One2many('budget.master.plan.approval', 'master_plan_id',
                                               string='Approval/Rejection/Return History')

    @property
    def _approval_model(self):
        return 'budget.master.plan.approval'

    @property
    def _approval_line(self):
        return self.master_plan_approval_ids

    @property
    def _approval_state(self):
        return 'kuec_approval_state'

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_master_plan_id': self.id
        }

    def _perform_common_action(self, state, group_xml_id):
        summary = _("Budget Master Plan Request Requires Your Review")
        note = _(
            f"The Budget Master Plan Request has been approved by {self.env.user.display_name} "
            "Please review the submitted Budget Master Plan Request and proceed with the next steps."
        )
        users = self._get_group_users(group_xml_id)
        self._perform_action(state, users, summary, note)

    def action_lock(self):
        self.ensure_one()
        self.is_readonly = True

    def action_unlock(self):
        self.ensure_one()
        self.is_readonly = False

    def submit_for_approval(self):
        self.ensure_one()
        summary = _("Budget Master Plan Request Requires Your Review")
        note = _(
            f"The Budget Master Plan Request has been Requested by {self.env.user.display_name} "
            "Please review the submitted Budget Master Plan Request and proceed with the next steps."
        )
        self.action_lock()
        for rec in self.budget_ids:
            rec.action_lock()
        users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
        self._perform_action('finance_procurement_approval', users, summary, note)

    def action_head_fin_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('coe_approval',
                                        'kaz_kuec_overall_doa_approval.group_coe_kuec')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_head_fin_approval')

    def action_coe_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('ceo_approval',
                                        'kaz_procurement_doa_kuec.group_kuec_ceo')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_coe_approval')

    def action_ceo_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_action('approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ceo_approval')

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Budget Master Plan Request Rejected")
            note = _(
                f"The Budget Master Plan Request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Budget Master Plan Request"
            )
            self._perform_action('rejected', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Reject Budget Master Plan', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Budget Master Plan Request Returned for Correction")
            note = _(
                f"The Budget Master Plan Request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Budget Master Plan Request"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')
