# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields, models, _


class HrInternshipReward(models.Model):
    _name = 'hr.internship.reward'
    _inherit = ['hr.internship.reward', 'approval.base.mixin']

    reward_approval_ids = fields.One2many('hr.internship.reward.approval', 'reward_id',
                                          string="Approval/Rejection/Return History")

    @property
    def _approval_model(self):
        return 'hr.internship.reward.approval'

    @property
    def _approval_line(self):
        return self.reward_approval_ids

    @property
    def _approval_state(self):
        return 'state'

    def _approval_context(self):
        self.ensure_one()
        return {
            'default_reward_id': self.id
        }

    def action_submit_for_approval(self):
        super().action_submit_for_approval()
        users = self._get_group_users('kaz_procurement_doa_kuec.group_kuec_ceo')
        for user in users:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                user_id=user.id,
                summary=_('Approval of Reward for Internship'),
                note=_('Please approve the reward request for Internship'),
                date_deadline=fields.Date.today() + timedelta(days=3)
            )

    def action_approve(self):
        """CEO approves reward"""
        self.ensure_one()
        if self._context.get('signed', False):
            super().action_approve()
            self._mark_activity_done()
            return True
        else:
            return self._open_approve_reject_wizard('Approve Internship', 'approve',
                                                    'action_approve')

    def action_reject(self):
        """CEO rejects reward"""
        self.ensure_one()
        if self._context.get('signed', False):
            super().action_reject()
            self._mark_activity_done()
            return True
        else:
            return self._open_approve_reject_wizard('Reject Internship', 'reject',
                                                    'action_reject')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            summary = _("Internship Reward Form Returned for Correction")
            note = _(
                f"The Internship Reward form has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Internship Reward form"
            )
            self._perform_action('draft', self.create_uid, summary, note)
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    def action_notify_accounting(self):
        """Notify accounting team and move to in_payment state"""
        self.state = 'in_payment'
        self.message_post(body=_("Accounting team has been notified for payment processing."))
        users = self.sudo()._get_group_users('account.group_account_basic').filtered(
            lambda user: user.sudo().company_id.company_code in ['KUEC'])
        # Create activity for accounting team to process payment
        for user in users:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary=_('Process Payment for Reward: %s') % self.name,
                note=_(
                    'Reward approved and ready for payment processing.\n\nInternship: %s\nAmount: AED %.2f\nPayment Reference: %s') % (
                         self.internship_id.name,
                         self.amount,
                         self.payment_reference or 'To be generated'
                     ),
                user_id=user.id
            )
