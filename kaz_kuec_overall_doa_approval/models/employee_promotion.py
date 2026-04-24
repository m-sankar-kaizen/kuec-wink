# -*- coding: utf-8 -*-
from odoo import fields, models, _


class EmployeePromotion(models.Model):
    _name = 'employee.promotion'
    _inherit = ['employee.promotion', 'approval.base.mixin']

    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('ccoe_approval', 'CCOE Approval'),
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
    promotion_approval_ids = fields.One2many('employee.promotion.approval',
                                             'employee_promotion_id',
                                             string='Approval/Rejection/Return History')

    @property
    def _approval_model(self):
        return 'employee.promotion.approval'

    @property
    def _approval_line(self):
        return self.promotion_approval_ids

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_employee_promotion_id': self.id
        }

    def action_submit(self):
        super().action_submit()
        self.submit_to_approve()

    def submit_to_approve(self):
        self.ensure_one()
        summary = _("Employee Promotion Request Requires Your Review")
        note = _(
            f"The Employee Promotion Request has been Requested by {self.env.user.display_name} "
            "Please review the submitted Employee Promotion Request and proceed with the next steps."
        )
        users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_head_department')
        ho_hr = self._get_group_users('kaz_kuec_overall_doa_approval.group_kuec_employee_hohr')
        users |= ho_hr
        self._perform_action('department_approval', users, summary, note)

    def _perform_common_action(self, state, group_xml_id):
        summary = _("Employee Promotion Request Requires Your Review")
        note = _(
            f"The Employee Promotion Request has been Requested by {self.env.user.display_name} "
            "Please review the submitted Employee Promotion Request and proceed with the next steps."
        )
        users = self._get_group_users(group_xml_id)
        self._perform_action(state, users, summary, note)

    def action_hod_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('ccoe_approval', 'kaz_procurement_doa_kuec.group_kuec_ccoe')

            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_hod_approval')

    def action_ccoe_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('ceo_approval', 'kaz_procurement_doa_kuec.group_kuec_ceo')
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ccoe_approval')

    def action_ceo_approval(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self.action_approve()
            self._perform_action('approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve', 'action_ceo_approval')

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Employee Promotion Request Rejected")
            note = _(
                f"The Employee Promotion Request has been rejected by {self.env.user.display_name}. "
                "Please review the submitted Employee Promotion Request"
            )
            self.state = 'rejected'
            self._perform_action('rejected', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Reject Employee Promotion Request', 'reject',
                                                    'action_reject_request')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Employee Promotion Request Returned for Correction")
            note = _(
                f"The Employee Promotion Request has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Employee Promotion Request"
            )
            self.state = 'cancelled'
            self._perform_action('draft', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')
