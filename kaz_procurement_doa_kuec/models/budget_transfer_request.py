# -*- coding: utf-8 -*-
from odoo import models, fields, _, api, Command
from odoo.exceptions import ValidationError


class BudgetTransferRequest(models.Model):
    _name = 'budget.transfer.request'
    _inherit = ['budget.transfer.request', 'mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one('res.company', string="Company",
                                 default=lambda self: self.env.company)
    company_code = fields.Selection(related="company_id.company_code")
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('ccoe', 'CCOE Approval'),
            ('ceo', 'CEO Approval'),
            ('chairman', 'Chairman Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string="KUEC Approval State",
        default="ccoe",
        tracking=True,
        copy=False,
    )
    budget_transfer_request_approval_ids = fields.One2many(
        'budget.transfer.request.approval', 'budget_transfer_request_id',
        string="Approval/Rejection/Return History")
    chairman_approval_attachment = fields.Binary(string="Chairman Approval Attachment")
    hide_chairman_approval_attachment = fields.Boolean(string="Hide Chairman Approval Attachment",
                                                       compute="_compute_hide_chairman_approval_attachment")

    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'chairman_approval_attachment': '',
        })
        return super().copy(default=default)

    def _compute_hide_chairman_approval_attachment(self):
        for rec in self:
            rec.hide_chairman_approval_attachment = not (
                    rec.company_code in ['KUEC']
                    and rec.kuec_approval_state == 'chairman'
                    or rec.chairman_approval_attachment
            )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        message = _(
            "A new Budget Transfer Request has been created because the "
            "Purchase Requisition exceeded its allocated budget. "
            "Approval from CCOE is required to proceed."
        )
        for rec in res:
            rec.notify_users_in_group(
                'kaz_procurement_doa_kuec.group_kuec_ccoe',
                activity_note=message
            )
        return res

    def action_reject_request(self):
        if self._context.get('signed', False):
            self.kuec_approval_state = 'rejected'
            self.state = 'rejected'
            user = self.requisition_id.employee_id.user_id
            if user:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    note=_("Your Budget Transfer Request has been rejected.")
                )
            return True
        else:
            return self._open_approve_reject_wizard('Reject Budget Transfer Request', 'reject',
                                                    'action_reject_request')

    def _open_approve_reject_wizard(self, name, request_type, next_action):
        self.ensure_one()
        current_state_key = self.kuec_approval_state
        # Use fields_get to fetch the selection label
        current_state_display = \
            dict(self.fields_get(['kuec_approval_state'])['kuec_approval_state']['selection'])[
                current_state_key]
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'budget.transfer.request.approval',
            'views': [(False, 'form')],
            'context': {
                'default_sequence': len(self.budget_transfer_request_approval_ids) + 1,
                'default_request_type': request_type,
                'default_parent_state_at_request': current_state_display,
                'default_next_action': next_action,
                'default_budget_transfer_request_id': self.id
            }
        }

    def _get_total_request_amount(self):
        return sum(self.line_ids.mapped('amount'))

    def action_approve_ccoe(self):
        if self._context.get('signed', False):
            total = self._get_total_request_amount()

            if total > 500_000:
                # Needs CEO approval
                self.kuec_approval_state = 'ceo'
                message = _(
                    "Budget Transfer Request requires CEO approval because the amount "
                    "exceeds AED 500,000."
                )

                self.notify_users_in_group(
                    'kaz_procurement_doa_kuec.group_kuec_ceo',
                    activity_note=message
                )
            else:
                self.with_context(signed=True).action_approve_request()
            return True
        else:
            return self._open_approve_reject_wizard('Approve Budget Transfer Request',
                                                    'approve',
                                                    'action_approve_ccoe')

    def action_approve_ceo(self):
        if self._context.get('signed', False):
            total = self._get_total_request_amount()

            if total > 3_000_000:
                # Needs Chairman approval
                self.kuec_approval_state = 'chairman'
                message = _(
                    "Budget Transfer Request requires Chairman approval because the amount "
                    "exceeds AED 3,000,000."
                )

                self.notify_users_in_group(
                    'kaz_procurement_doa_kuec.group_kuec_chairman',
                    activity_note=message
                )
            else:
                self.with_context(signed=True).action_approve_request()
            return True
        else:
            return self._open_approve_reject_wizard('Approve Budget Transfer Request', 'approve',
                                                    'action_approve_ceo')

    def action_approve_request(self):
        if self._context.get('signed', False):
            self.button_second_approve()
            self.kuec_approval_state = 'approved'
            if not self.requisition_id.budget_warning_message:
                self.requisition_id.kuec_approval_state = 'finance_procurement_approval'
                self.requisition_id.notify_group_users(
                    'kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.create_uid.id,
                note=_("Your Budget Transfer Request has been fully approved.")
            )
            return True
        else:
            if not self.chairman_approval_attachment:
                raise ValidationError(
                    _("Please upload the Chairman Approval Attachment before approving."))
            return self._open_approve_reject_wizard('Approve Budget Transfer Request', 'approve',
                                                    'action_approve_request')

    def notify_users_in_group(self, group_xml_id, activity_note=None):
        """
        Fetch users from a group using external ID and send notifications.
        """

        # Fetch group
        try:
            group = self.env.ref(group_xml_id)
        except ValueError:
            raise ValidationError(
                _("The group '%s' does not exist. Please check the configuration.") % group_xml_id
            )

        # Fetch users
        users = group.users.filtered(lambda rec: rec.company_id.company_code in ['KUEC'])
        if not users:
            raise ValidationError(
                _("No users found in the group '%s'. Cannot send notifications.") % group_xml_id
            )

        # Notify each user
        for user in users:
            if activity_note:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    note=activity_note,
                )

        return True
