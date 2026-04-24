# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ExtendAgreement(models.Model):
    _inherit = 'extend.agreement'

    # Extend the existing state field with WINK multi-level approval stages.
    state = fields.Selection(
        selection_add=[
            ('coordinator_approval', 'Coordinator Approval'),
            ('department_approval', 'Department Approval'),
            ('ccoe_approval', 'CCOE Approval'),
            ('legal_approval', 'Legal Approval'),
            ('ceo_approval', 'CEO Approval'),
        ],
        ondelete={
            'coordinator_approval': 'set default',
            'department_approval': 'set default',
            'ccoe_approval': 'set default',
            'legal_approval': 'set default',
            'ceo_approval': 'set default',
        },
    )
    company_code = fields.Selection(related='company_id.company_code', string='Company Code')

    def _wink_notify_group(self, next_state, group_xml_id, summary, note):
        """Transition state and schedule activities for the next approver group."""
        self.state = next_state
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
            self._wink_notify_group(
                'coordinator_approval',
                'kaz_wink_approval_doa.group_wink_coordinator',
                _("Extension Request Requires Your Review"),
                _(
                    f"A new extension request for agreement {pr_name} has been submitted "
                    f"by {self.env.user.display_name}. "
                    f"Requested new end date: {self.new_date_end}. "
                    f"Please review and proceed."
                ),
            )
            return
        return super().action_notify()

    def action_coordinator_approval(self):
        """Coordinator approves — forward to Department Head."""
        self.ensure_one()
        self._wink_notify_group(
            'department_approval',
            'kaz_wink_approval_doa.group_wink_head_department',
            _("Extension Request Requires Your Review"),
            _(
                f"The extension request for {self.purchase_requisition_id.name or 'agreement'} "
                f"has been approved by Coordinator {self.env.user.display_name}. "
                f"Please review and proceed."
            ),
        )

    def action_hod_approval(self):
        """Department Head approves — forward to CCOE."""
        self.ensure_one()
        self._wink_notify_group(
            'ccoe_approval',
            'kaz_wink_approval_doa.group_wink_ccoe',
            _("Extension Request Requires Your Review"),
            _(
                f"The extension request for {self.purchase_requisition_id.name or 'agreement'} "
                f"has been approved by Department Head {self.env.user.display_name}. "
                f"Please review and proceed."
            ),
        )

    def action_ccoe_approval(self):
        """CCOE approves — forward to Legal Team."""
        self.ensure_one()
        self._wink_notify_group(
            'legal_approval',
            'kaz_wink_approval_doa.group_wink_legal_team',
            _("Extension Request Requires Your Review"),
            _(
                f"The extension request for {self.purchase_requisition_id.name or 'agreement'} "
                f"has been approved by CCOE {self.env.user.display_name}. "
                f"Please review and proceed."
            ),
        )

    def action_legal_approval(self):
        """Legal Team approves — forward to CEO."""
        self.ensure_one()
        self._wink_notify_group(
            'ceo_approval',
            'kaz_wink_approval_doa.group_wink_ceo',
            _("Extension Request Requires Your Review"),
            _(
                f"The extension request for {self.purchase_requisition_id.name or 'agreement'} "
                f"has been approved by Legal Team {self.env.user.display_name}. "
                f"Please review and proceed."
            ),
        )

    def action_ceo_approval(self):
        """CEO approves — mark approved and update the purchase agreement end date."""
        self.ensure_one()
        self.action_approve()

    def action_reject_request(self):
        """Reject the extension and notify the requester."""
        self.ensure_one()
        self.action_reject()
        if self.request_user_id:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                user_id=self.request_user_id.id,
                summary=_("Extension Request Rejected"),
                note=_(
                    f"Your extension request for "
                    f"{self.purchase_requisition_id.name or 'the agreement'} "
                    f"has been rejected by {self.env.user.display_name}."
                ),
            )
