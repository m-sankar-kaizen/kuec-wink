# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ExtendAgreement(models.Model):
    _inherit = 'extend.agreement'

    wink_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('coordinator_approval', 'Coordinator Approval'),
            ('department_approval', 'Department Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('legal_approval', 'Legal Approval'),
            ('ceo_approval', 'CEO Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='WINK Approval State',
        default='draft',
        tracking=True,
        copy=False,
    )
    company_code = fields.Selection(related='company_id.company_code', string='Company Code')

    def _wink_notify_group(self, next_state, group_xml_id, summary, note):
        """Transition wink_approval_state and schedule activities for the next group."""
        self.wink_approval_state = next_state
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if group and group.users:
            for user in group.users:
                self.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    user_id=user.id,
                    summary=summary,
                    note=note,
                )

    def action_notify(self):
        """For WINK, start coordinator approval instead of notifying KUEC managers."""
        self.ensure_one()
        if self.company_id.company_code == 'WINK':
            pr_name = self.purchase_requisition_id.name or ''
            summary = _("Extension Request Requires Your Review")
            note = _(
                f"A new extension request for agreement {pr_name} has been submitted "
                f"by {self.env.user.display_name}. "
                f"Requested new end date: {self.new_date_end}. "
                f"Please review and proceed."
            )
            self._wink_notify_group(
                'coordinator_approval',
                'kaz_wink_approval_doa.group_wink_coordinator',
                summary,
                note,
            )
            return
        return super().action_notify()

    def action_coordinator_approval(self):
        """Coordinator approves — forward to Department Head."""
        self.ensure_one()
        pr_name = self.purchase_requisition_id.name or ''
        self._wink_notify_group(
            'department_approval',
            'kaz_wink_approval_doa.group_wink_head_department',
            _("Extension Request Requires Your Review"),
            _(
                f"The extension request for agreement {pr_name} has been approved by "
                f"Coordinator {self.env.user.display_name}. Please review and proceed."
            ),
        )

    def action_hod_approval(self):
        """Department Head approves — forward to CCOE."""
        self.ensure_one()
        pr_name = self.purchase_requisition_id.name or ''
        self._wink_notify_group(
            'ccoe_approval',
            'kaz_wink_approval_doa.group_wink_ccoe',
            _("Extension Request Requires Your Review"),
            _(
                f"The extension request for agreement {pr_name} has been approved by "
                f"Department Head {self.env.user.display_name}. Please review and proceed."
            ),
        )

    def action_ccoe_approval(self):
        """CCOE approves — forward to Legal Team."""
        self.ensure_one()
        pr_name = self.purchase_requisition_id.name or ''
        self._wink_notify_group(
            'legal_approval',
            'kaz_wink_approval_doa.group_wink_legal_team',
            _("Extension Request Requires Your Review"),
            _(
                f"The extension request for agreement {pr_name} has been approved by "
                f"CCOE {self.env.user.display_name}. Please review and proceed."
            ),
        )

    def action_legal_approval(self):
        """Legal Team approves — forward to CEO."""
        self.ensure_one()
        pr_name = self.purchase_requisition_id.name or ''
        self._wink_notify_group(
            'ceo_approval',
            'kaz_wink_approval_doa.group_wink_ceo',
            _("Extension Request Requires Your Review"),
            _(
                f"The extension request for agreement {pr_name} has been approved by "
                f"Legal Team {self.env.user.display_name}. Please review and proceed."
            ),
        )

    def action_ceo_approval(self):
        """CEO approves — mark as approved and update the PR end date."""
        self.ensure_one()
        self.wink_approval_state = 'approved'
        self.action_approve()

    def action_reject_request(self):
        """Reject the extension request and notify the requester."""
        self.ensure_one()
        self.wink_approval_state = 'rejected'
        self.action_reject()
        if self.request_user_id:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                user_id=self.request_user_id.id,
                summary=_("Extension Request Rejected"),
                note=_(
                    f"Your extension request for agreement "
                    f"{self.purchase_requisition_id.name or ''} "
                    f"has been rejected by {self.env.user.display_name}."
                ),
            )
