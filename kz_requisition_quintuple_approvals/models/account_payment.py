# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountPayment(models.Model):
    """
    Extends the `account.payment` model to implement a multi-level approval
    workflow for payments, based on the amount and type (inbound/outbound),
    and integrates approval tracking, state transitions, and user notifications.

    Features:
    - Distinguishes between advance and regular payments.
    - Tracks approval progress via `approvement_state`.
    - Assigns payment approval responsibilities based on amount thresholds.
    - Schedules activities to notify relevant user groups during approval.
    """
    _inherit = "account.payment"

    is_advance_payment = fields.Selection(
        selection=[('yes', 'Yes'), ('no', 'No')],
        string='Advance Payment',
        default='no',
        help="Indicates whether this payment is an advance."
    )

    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        help="Associated purchase order if this is an advance payment."
    )

    approvement_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending', 'Pending Approval'),
            ('head_of_unit_approval', 'Head of Unit Approved'),
            ('hof_approval', 'HOF Approved'),
            ('ceo_approval', 'CEO Approved'),
            ('board_approval', 'Board Approved'),
            ('shareholders_approval', 'Shareholders Approved'),
            ('approved', 'Approved'),
            ('confirmed', 'Confirmed'),
        ],
        string='Approval State',
        default='draft',
        copy=False,
        help="Tracks the multi-stage approval state of this payment."
    )

    final_approve = fields.Boolean(
        string='Final Approval',
        copy=False,
        help="Indicates if the final approval has been granted."
    )

    company_code = fields.Selection(related='company_id.company_code')

    current_group = fields.Char(
        string='Current Approval Group',
        readonly=True,
        copy=False,
        help="Internal technical field tracking current approval group."
    )

    show_confirm = fields.Boolean(
        string='Show Confirm Button',
        compute='_compute_show_confirm',
        help="Controls visibility of the 'Confirm' button based on approval logic."
    )

    @api.depends('payment_type', 'state', 'approvement_state', 'is_advance_payment')
    def _compute_show_confirm(self):
        """
        Determines whether the 'Confirm' button should be shown.
        Regular payments can be confirmed in draft state.
        Advance payments require approval first.
        """
        for rec in self:
            if rec.is_advance_payment == 'no' and rec.state == 'draft':
                rec.show_confirm = True
            elif rec.is_advance_payment == 'yes' and rec.approvement_state == 'approved' and rec.state == 'draft':
                rec.show_confirm = True
            else:
                rec.show_confirm = False

    @api.onchange('is_advance_payment')
    def onchange_is_advance_payment(self):
        """
        Clears the purchase ID if not an advance payment.
        Prints message history for debug/inspection.
        """
        if self.is_advance_payment == 'no':
            self.purchase_id = False

    @api.onchange('payment_type')
    def onchange_payment_types(self):
        """
        If payment type is inbound (receiving), clear related fields
        since no approval is required for such cases.
        """
        if self.payment_type == 'inbound':
            self.purchase_id = False
            self.is_advance_payment = 'no'

    def submit_to_approve(self):
        """
        Initializes approval workflow by marking payment as pending
        and sending approval notification to the first required group.
        """
        self.approvement_state = 'pending'
        approval_flow = self.get_groups(self.payment_type, self.amount)
        if approval_flow:
            group = approval_flow[0]
            self.notify_group(group)

    def get_groups(self, type, amount):
        """
        Resolves approval group list based on payment amount and type.

        :param type: str, 'inbound' or 'outbound'
        :param amount: float, payment amount
        :return: list of group XML IDs (str)
        """
        groups = []
        if type == 'outbound':
            if 0 <= amount <= 250000:
                groups = ['head_of_unit', 'hof']
            elif 250000 < amount <= 1000000:
                groups = ['hof', 'ceo']
            elif 1000000 < amount <= 5000000:
                groups = ['board']
            elif amount > 5000000:
                groups = ['shareholders']
        return groups

    def get_group_name(self, group):
        """
        Converts simple group code to full XML record name.

        :param group: str, e.g. 'hof'
        :return: full record name string
        """
        return 'kz_requisition_quintuple_approvals.' + group if group else ''

    def button_approve(self):
        """
        Advances the approval state if the user belongs to the current required group.
        Triggers notification to next approver, or finalizes if end of flow.
        """
        approval_flow = self.get_groups(self.payment_type, self.amount)
        if not approval_flow:
            return

        if not self.current_group:
            group = approval_flow[0]
            group_name = self.get_group_name(group)
            if self.env.user.has_group(group_name):
                self.approvement_state = group + '_approval'
                self.current_group = group
                if len(approval_flow) > 1:
                    self.notify_group(approval_flow[1])
            else:
                self.notify_group(group)
        else:
            new_index = approval_flow.index(self.current_group) + 1
            if new_index < len(approval_flow):
                group = approval_flow[new_index]
                group_name = self.get_group_name(group)
                if self.env.user.has_group(group_name):
                    self.approvement_state = group + '_approval'
                    self.current_group = group
                    if new_index + 1 < len(approval_flow):
                        self.notify_group(approval_flow[new_index + 1])
                else:
                    self.notify_group(group)

            if new_index == len(approval_flow) - 1:
                self.final_approve = True
                self.approvement_state = 'approved'

    def notify_group(self, group):
        """
        Schedules approval activity for all users in the specified group.

        :param group: str, group code, e.g. 'hof', 'ceo'
        :return: success toast action
        """
        if group:
            group_name = self.get_group_name(group)
            approve_group = self.env.ref(group_name)
            users = approve_group.users
            if users:
                for user in users:
                    self.activity_schedule(
                        'kz_requisition_quintuple_approvals.mail_payment_approval',
                        user_id=user.id,
                        note=_("Please approve payment request %s") % self.name
                    )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _("Approve request has been sent"),
                    'sticky': False,
                }
            }

    def return_to_draft(self):
        """
        Resets approval state and related fields to allow editing/resubmission.
        """
        self.approvement_state = 'draft'
        self.current_group = ''
        self.final_approve = False

    def action_draft(self):
        """
        Overrides native draft action to also reset approval tracking fields.
        """
        super().action_draft()
        self.return_to_draft()

    def action_post(self):
        """
        Overrides `post` action to set final approval state.
        """
        result = super().action_post()
        self.approvement_state = 'confirmed'
        return result
