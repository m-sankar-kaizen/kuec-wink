# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import ValidationError


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    department_id = fields.Many2one(related='employee_id.department_id', string='Department')
    kuec_approval_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('department_approval', 'Department Approval'),
            ('budget_control', 'Budget Control'),
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
    employee_hod_id = fields.Many2one(related='employee_id.parent_id', string='Department Head')
    is_unbudgeted = fields.Boolean(string="Is Unbudgeted", copy=False)
    material_purchase_requisition_approval_ids = fields.One2many(
        'material.purchase.requisition.approval', 'requisition_id',
        string="Approval/Rejection/Return History")
    board_approval_attachment = fields.Binary(string="Board Approval Attachment", copy=False)
    hide_board_approval_attachment = fields.Boolean(string="Hide Board Approval Attachment",
                                                    compute="_compute_hide_board_approval_attachment")

    purchase_vendor_active = fields.Boolean(
        string="Purchase Vendor Active",
        compute="_compute_purchase_vendor_active",
        store=True,
    )
    purchase_requisition_type = fields.Selection(
        selection=[
            ('capex', "Capex"),
            ('opex', "Opex"),
        ],
        required=True,
        string="Purchase Requisition Type",
    )
    service_receipt_ids = fields.Many2many("service.receipt",
                                           string="Service Receipt",
                                           compute='_compute_service_receipt_ids')
    incoming_service_count = fields.Integer("Incoming Service count",
                                            compute='_compute_incoming_service_count')

    @api.depends('company_id', 'req_type', 'requisition_type_id')
    def _compute_purchase_vendor_active(self):
        for rec in self:
            if rec.company_code != 'KUEC':
                # Always visible and required for other companies
                rec.purchase_vendor_active = True
            else:
                # KUEC specific conditions
                if rec.req_type in ['variation', 'repeated'] or \
                        (rec.requisition_type_id and rec.requisition_type_id.is_tender):
                    rec.purchase_vendor_active = False
                else:
                    rec.purchase_vendor_active = True

    def _compute_hide_board_approval_attachment(self):
        for rec in self:
            rec.hide_board_approval_attachment = not (
                    rec.kuec_approval_state == 'board_approval'
                    or rec.board_approval_attachment
            )

    def _check_company_access(self):
        return self.company_code in ['KUEC']

    def action_approve_kuec_pr(self):
        if self._check_company_access():
            if self._context.get('signed', False):
                self.kuec_approval_state = 'approved'
                self.approvement_state = 'approved'
                self.notify_creator(
                    f"A Purchase order/Tender is ready to be created on purchase requisition {self.name}")
                return True
            else:
                if not self.board_approval_attachment:
                    raise ValidationError(
                        _("Please upload the Board Approval Attachment before approving."))
                return self._open_approve_reject_wizard('Approve Requisition', 'approve',
                                                        'action_approve_kuec_pr')
        else:
            return False

    def action_kuec_ceo_approve(self):
        if self._context.get('signed', False):
            self.close_activity(self.env.user)
            if self.purchase_requisition_type == 'capex':
                amount = 5_000_000 if self.is_unbudgeted else 10_000_000
                approve = self.amount_incurrency <= amount
            else:
                if self.req_type == 'variation':
                    approve = self.amount_incurrency <= 5_000_000
                else:
                    amount = 10_000_000 if self.is_tender else 2_000_000
                    approve = self.amount_incurrency <= amount
            if approve:
                self.with_context(signed=True).action_approve_kuec_pr()
            else:
                self.kuec_approval_state = 'board_approval'
                self.notify_group_users('kaz_procurement_doa_kuec.group_kuec_board')

            # amount = 5_000_000 if self.is_unbudgeted else 10_000_000
            # if self.amount_incurrency > amount:
            #     self.kuec_approval_state = 'board_approval'
            #     self.notify_group_users('kaz_procurement_doa_kuec.group_kuec_board')
            # else:
            #     self.with_context(signed=True).action_approve_kuec_pr()
            # return True
        else:
            return self._open_approve_reject_wizard('Approve Requisition', 'approve',
                                                    'action_kuec_ceo_approve')

    def action_kuec_ccoe_approve(self):
        if self._context.get('signed', False):
            self.close_activity(self.env.user)
            if self.purchase_requisition_type == 'capex':
                amount = 1_000_000 if self.is_unbudgeted else 5_000_000
                approve = self.amount_incurrency <= amount
            else:
                if self.req_type == 'variation':
                    approve = self.amount_incurrency <= 250_000
                else:
                    amount = 3_000_000 if self.is_tender else 500_000
                    approve = self.amount_incurrency <= amount
            if approve:
                self.with_context(signed=True).action_approve_kuec_pr()
            else:
                self.kuec_approval_state = 'ceo_approval'
                self.notify_group_users('kaz_procurement_doa_kuec.group_kuec_ceo')

            # amount = 1_000_000 if self.is_unbudgeted else 5_000_000
            # if self.amount_incurrency > amount:
            #     self.kuec_approval_state = 'ceo_approval'
            #     self.notify_group_users('kaz_procurement_doa_kuec.group_kuec_ceo')
            # else:
            #     self.with_context(signed=True).action_approve_kuec_pr()
            return True
        else:
            return self._open_approve_reject_wizard('Approve Requisition', 'approve',
                                                    'action_kuec_ccoe_approve')

    def action_finance_procurement_approve(self):
        if self._context.get('signed', False):
            self.close_activity(self.env.user)
            if self.purchase_requisition_type == 'capex':
                approve = False
            else:
                if self.req_type == 'variation':
                    approve = False
                else:
                    amount = 1_000_000 if self.is_tender else 50_000
                    approve = self.amount_incurrency <= amount

            if approve:
                self.with_context(signed=True).action_approve_kuec_pr()
            else:
                self.notify_group_users('kaz_procurement_doa_kuec.group_kuec_ccoe')
                self.kuec_approval_state = 'ccoe_approval'
            return True
        else:
            return self._open_approve_reject_wizard('Approve Requisition', 'approve',
                                                    'action_finance_procurement_approve')

    def action_budget_transfer_request(self):
        if self._context.get('signed', False):
            self.close_activity(self.env.user)
            return self._get_approve_wizard()
        else:
            return self._open_approve_reject_wizard('Approve Requisition', 'approve',
                                                    'action_budget_transfer_request')

    def action_hod_approve(self):
        if self._check_company_access():
            if self.env.user != self.employee_hod_id.user_id:
                raise ValidationError(
                    _("You are not allowed to approve this requisition. Only the assigned Department Head can approve.")
                )
            if self._context.get('signed', False):
                self.close_activity(self.env.user)
                if self.budget_warning_message:
                    self.is_unbudgeted = True
                    self.kuec_approval_state = 'budget_control'
                    self.notify_group_users('kaz_procurement_doa_kuec.group_kuec_budget')
                else:
                    self.kuec_approval_state = 'finance_procurement_approval'
                    self.notify_group_users(
                        'kaz_procurement_doa_kuec.group_kuec_head_fin_procurement')
                return True
            else:
                return self._open_approve_reject_wizard('Approve Requisition', 'approve',
                                                        'action_hod_approve')
        return False

    def get_group_users(self, group):
        """Return users in the specified group who belong to KUEC."""
        try:
            groups = self.env.ref(group)
        except ValueError:
            raise ValidationError(
                _("The approval group '%s' does not exist. Please contact the system administrator.") % group
            )

        users = groups.users.filtered(lambda user: user.company_id.company_code in ['KUEC'])
        return users, groups

    def notify_group_users(self, group):
        """Notify the next approval group users."""
        users, groups = self.get_group_users(group)

        if not users:
            raise ValidationError(
                _("No eligible users found in the group '%s' for company KUEC. "
                  "Please check access rights configuration.") % groups.name
            )

        for user in users:
            # email notification
            self.action_send_requisition_approval_email(user, "New requisition needs approval")

            # activity assignment
            self.activity_schedule(
                'kz_requisition_quintuple_approvals.mail_requisition_approval',
                user_id=user.id,
                note=f"Requisition {self.name} needs your approval."
            )

        # Approval line history
        self.create_submit_approval_line(users)

    def get_department_head_users(self):
        if self._check_company_access():
            manager = self.employee_hod_id
            if not manager:
                raise ValidationError(
                    _("No department head found. Please assign a manager to the employee’s department.")
                )
            if not manager.user_id:
                raise ValidationError(
                    _("The department head does not have a linked user. Please configure a user for the manager.")
                )
            return manager.user_id
        else:
            return super().get_department_head_users()

    def submit_to_approve(self):
        super().submit_to_approve()
        if self._check_company_access():
            self.kuec_approval_state = 'department_approval'

    def action_reject_requisition(self):
        if self._check_company_access():
            if self._context.get('signed', False):
                self.requisition_reject()
                self.kuec_approval_state = 'rejected'
                return True
            else:
                return self._open_approve_reject_wizard('Reject Requisition', 'reject',
                                                        'action_reject_requisition')
        return False

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
            'res_model': 'material.purchase.requisition.approval',
            'views': [(False, 'form')],
            'context': {
                'default_sequence': len(self.material_purchase_requisition_approval_ids) + 1,
                'default_request_type': request_type,
                'default_parent_state_at_request': current_state_display,
                'default_next_action': next_action,
                'default_requisition_id': self.id
            }
        }

    def requisition_rfc(self):
        if self._check_company_access():
            if self._context.get('signed', False):
                self.notify_creator(f"The PR {self.name} has Been Returned for correction")
                self.reset_draft_requisition()
                return True
            else:
                return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                        'requisition_rfc')
        return False

    def reset_draft_requisition(self):
        if self._check_company_access():
            self.reset_draft()
            self.approvement_state = 'draft'
            self.kuec_approval_state = 'draft'

    def action_cancel_requisition(self):
        if self._check_company_access():
            self.action_cancel()
            self.approvement_state = 'cancel'
            self.kuec_approval_state = 'cancel'

    @api.depends('purchase_ids', 'purchase_ids.service_receipt_ids')
    def _compute_service_receipt_ids(self):
        for record in self:
            record.service_receipt_ids = record.purchase_ids.service_receipt_ids

    @api.depends('service_receipt_ids')
    def _compute_incoming_service_count(self):
        """
        Compute method for the `incoming_service_count` field.

        Sets the number of associated `service.receipt` records (excluding done/cancelled).
        """
        for record in self:
            record.incoming_service_count = len(record.service_receipt_ids)

    def action_view_product(self):
        """
        Open related `service.receipt` records in a view.

        """
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id(
            'skit_srn_receipt.action_service_receipt_all')
        result['domain'] = [('id', 'in', self.service_receipt_ids.ids)]
        return result
